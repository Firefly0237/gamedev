import json
import os
import re
import time
from pathlib import Path

from config.logger import logger
from scanner.base import BaseScanner, ProjectContext
from scanner.coverage import analyze_coverage
from scanner.reference_graph import build_reference_graph, extract_references


SKIP_DIRS = {"Library", "Temp", "Packages", "obj", ".git"}
GENRE_KEYWORDS = {
    "rpg": ["inventory", "quest", "dialogue", "npc", "skill", "level_up", "save", "load", "experience"],
    "action": ["weapon", "health", "damage", "shoot", "projectile", "controller", "aim", "reload"],
    "strategy": ["unit", "tile", "grid", "fog", "build", "resource", "select", "command", "formation"],
    "simulation": ["resource", "time", "schedule", "place", "farm", "craft", "npc", "production"],
    "moba_sport": ["hero", "lane", "minion", "tower", "ability", "cooldown", "match", "rank"],
}


class UnityScanner(BaseScanner):
    def __init__(self, project_path: str):
        super().__init__(project_path)
        self.project_root = Path(project_path).resolve()
        self.assets_root = self.project_root / "Assets"
        self._script_list: list[str] = []
        self._config_list: list[str] = []
        self._shader_list: list[str] = []
        self._localization_list: list[str] = []
        self._scripts_with_refs: list[dict] = []

    def validate_project(self) -> tuple[bool, str]:
        if not (self.project_root / "ProjectSettings").exists():
            return False, "缺少 ProjectSettings/"
        if not self.assets_root.exists():
            return False, "缺少 Assets/"
        if not (self.project_root / "ProjectSettings" / "ProjectVersion.txt").exists():
            return False, "缺少 ProjectSettings/ProjectVersion.txt"
        return True, ""

    def _cache_path(self) -> Path:
        return self.project_root / ".gamedev_cache.json"

    def _load_cache(self) -> dict:
        cache_file = self._cache_path()
        if not cache_file.exists():
            return {}
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(f"缓存加载失败: {exc}")
            return {}

    def _save_cache(self, scripts: list[dict], scan_time: float) -> None:
        cache = {"scan_time": scan_time, "files": {}}
        for script in scripts:
            rel_path = script.get("path", "")
            if not rel_path:
                continue
            full_path = self.project_root / rel_path
            try:
                mtime = full_path.stat().st_mtime
            except OSError:
                mtime = 0
            cache["files"][rel_path] = {
                "mtime": mtime,
                "skeleton": {key: value for key, value in script.items() if key != "_raw_references"},
                "references": sorted(script.get("_raw_references", set())),
            }
        try:
            self._cache_path().write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning(f"缓存保存失败: {exc}")

    def clear_cache(self) -> None:
        cache_file = self._cache_path()
        if cache_file.exists():
            cache_file.unlink()
            logger.info("缓存已清除")

    def scan(self) -> ProjectContext:
        scan_start = time.time()
        scripts = self._scan_scripts(incremental=True)
        scenes = self._scan_scenes()
        prefabs = self._scan_assets()
        configs = self._scan_configs()
        shaders = self._scan_shaders()
        localization = self._scan_localization()

        self._auto_generate_schemas(configs)
        detected_genre = self.detect_genre(scripts)
        reference_graph, reverse_graph, class_to_path = build_reference_graph(self._scripts_with_refs)

        ctx = ProjectContext(
            project_path=str(self.project_root),
            engine="unity",
            engine_version=self._get_engine_version(),
            detected_genre=detected_genre,
            scripts=scripts,
            scenes=scenes,
            assets=prefabs,
            config_files=configs,
            localization_files=localization,
            shader_files=shaders,
            prefabs=prefabs,
            directory_tree=self._build_directory_tree(),
            total_scripts=len(scripts),
            reference_graph=reference_graph,
            reverse_graph=reverse_graph,
            class_to_path=class_to_path,
            last_scan_time=scan_start,
        )

        coverage = analyze_coverage(ctx.scripts)
        ctx.test_files = coverage["test_files"]
        ctx.covered_classes = coverage["covered_classes"]
        ctx.uncovered_scripts = coverage["uncovered_scripts"]
        ctx.test_coverage_ratio = coverage["coverage_ratio"]

        self._save_cache(self._scripts_with_refs, scan_start)
        return ctx

    def _relpath(self, path: Path) -> str:
        return os.path.relpath(path, self.project_root)

    def _get_engine_version(self) -> str:
        version_file = self.project_root / "ProjectSettings" / "ProjectVersion.txt"
        if not version_file.exists():
            return "unknown"

        content = version_file.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"m_EditorVersion:\s*([^\s]+)", content)
        return match.group(1) if match else "unknown"

    def _build_namespace_to_classes(self, scripts: list[dict]) -> dict[str, list[str]]:
        namespace_to_classes: dict[str, list[str]] = {}
        for script in scripts:
            namespace = script.get("namespace", "")
            class_name = script.get("class_name", "")
            if not namespace or not class_name:
                continue
            namespace_to_classes.setdefault(namespace, [])
            if class_name not in namespace_to_classes[namespace]:
                namespace_to_classes[namespace].append(class_name)
        return namespace_to_classes

    def _scan_scripts(self, incremental: bool = True) -> list[dict]:
        scripts: list[dict] = []
        parsed_items: list[tuple[dict, str]] = []
        cache = self._load_cache() if incremental else {}
        cached_files = cache.get("files", {})
        reused = 0
        parsed = 0
        self._script_list = []
        self._scripts_with_refs = []

        for path in sorted(self.assets_root.rglob("*.cs")):
            if any(part in SKIP_DIRS or part == "Plugins" for part in path.parts):
                continue
            rel_path = self._relpath(path)
            self._script_list.append(rel_path)
            current_mtime = path.stat().st_mtime
            cached = cached_files.get(rel_path)

            if cached and cached.get("mtime") == current_mtime:
                skeleton = dict(cached.get("skeleton", {}))
                scripts.append(skeleton)
                with_refs = dict(skeleton)
                with_refs["_raw_references"] = set(cached.get("references", []))
                self._scripts_with_refs.append(with_refs)
                reused += 1
                continue

            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                skeleton = self._parse_csharp(content, rel_path)
            except Exception as exc:
                logger.warning(f"脚本解析失败: {rel_path} ({exc})")
                continue

            parsed_items.append((skeleton, content))
            scripts.append(skeleton)
            parsed += 1

        namespace_to_classes = self._build_namespace_to_classes(scripts)
        for skeleton, content in parsed_items:
            with_refs = dict(skeleton)
            with_refs["_raw_references"] = extract_references(content, namespace_to_classes)
            self._scripts_with_refs.append(with_refs)

        logger.info(f"扫描完成：复用 {reused}，新解析 {parsed}，总共 {len(scripts)} 个脚本")
        return scripts

    def _parse_csharp(self, content: str, path: str) -> dict:
        namespace_match = re.search(r"namespace\s+([\w.]+)", content)
        class_match = re.search(
            r"(?:public|private|internal)?\s*(?:abstract|sealed|static)?\s*class\s+(\w+)(?:\s*:\s*([\w.,\s]+))?",
            content,
        )
        public_fields = re.findall(
            r"\[?(?:SerializeField|Header\(\".*?\"\))?\]?\s*public\s+(\w+[\[\]<>]*)\s+(\w+)",
            content,
        )
        public_methods = re.findall(
            r"public\s+(?:static\s+)?(?:virtual\s+)?(?:override\s+)?(\w+[\[\]<>]*)\s+(\w+)\s*\(",
            content,
        )
        unity_methods = sorted(
            set(
                re.findall(
                    r"\b(?:public|private|protected|internal)?\s*(?:void|IEnumerator)\s+"
                    r"(Awake|Start|Update|FixedUpdate|LateUpdate|OnEnable|OnDisable)\s*\(",
                    content,
                )
            )
        )

        return {
            "path": path,
            "class_name": class_match.group(1) if class_match else "",
            "base_class": class_match.group(2).strip() if class_match and class_match.group(2) else "",
            "namespace": namespace_match.group(1) if namespace_match else "",
            "public_fields": [{"type": field_type, "name": field_name} for field_type, field_name in public_fields],
            "public_methods": [
                {"return_type": return_type, "name": method_name}
                for return_type, method_name in public_methods
            ],
            "unity_methods": unity_methods,
        }

    def _scan_scenes(self) -> list[str]:
        return [self._relpath(path) for path in sorted(self.assets_root.rglob("*.unity"))]

    def _scan_assets(self) -> list[str]:
        return [self._relpath(path) for path in sorted(self.assets_root.rglob("*.prefab"))]

    def _scan_configs(self) -> list[str]:
        configs: list[str] = []
        for path in sorted(self.assets_root.rglob("*.json")):
            if "Packages" in path.parts:
                continue
            configs.append(self._relpath(path))
        self._config_list = configs
        return configs

    def _scan_shaders(self) -> list[str]:
        shader_paths = sorted(list(self.assets_root.rglob("*.shader")) + list(self.assets_root.rglob("*.shadergraph")))
        self._shader_list = [self._relpath(path) for path in shader_paths]
        return self._shader_list

    def _scan_localization(self) -> list[str]:
        results: list[str] = []
        for path in sorted(self.assets_root.rglob("*.json")):
            rel_path = self._relpath(path)
            lower_path = rel_path.lower()
            file_name = path.name.lower()
            if (
                "locali" in file_name
                or "i18n" in file_name
                or "lang" in file_name
                or "localization" in lower_path
            ):
                results.append(rel_path)
        self._localization_list = results
        return results

    def _build_directory_tree(self, max_depth=2) -> str:
        lines: list[str] = ["Assets/"]

        def walk(path: Path, prefix: str, depth: int) -> None:
            if depth >= max_depth:
                return

            entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            for entry in entries:
                if entry.name in SKIP_DIRS:
                    continue
                suffix = "/" if entry.is_dir() else ""
                rel_depth = len(entry.relative_to(self.assets_root).parts)
                lines.append(f"{prefix}{entry.name}{suffix}")
                if entry.is_dir() and rel_depth < max_depth:
                    walk(entry, prefix + "  ", depth + 1)

        walk(self.assets_root, "  ", 0)
        return "\n".join(lines)

    def _auto_generate_schemas(self, config_files: list[str]):
        schema_dir = Path(__file__).resolve().parents[1] / "context" / "project_schemas"
        schema_dir.mkdir(parents=True, exist_ok=True)
        current_outputs = {Path(rel_path).name for rel_path in config_files}

        for existing_file in schema_dir.glob("*.json"):
            if existing_file.name not in current_outputs:
                try:
                    existing_file.unlink()
                except OSError as exc:
                    logger.warning(f"旧 Schema 清理失败: {existing_file.name} ({exc})")

        for rel_path in config_files:
            full_path = self.project_root / rel_path
            try:
                content = json.loads(full_path.read_text(encoding="utf-8", errors="ignore"))
            except Exception as exc:
                logger.warning(f"Schema 生成失败: {rel_path} ({exc})")
                continue

            sample_values: list[str] = []
            if isinstance(content, list):
                sample = content[0] if content else {}
                record_count = len(content)
                for item in content[:5]:
                    if isinstance(item, dict):
                        for value in item.values():
                            if isinstance(value, str) and value not in sample_values:
                                sample_values.append(value)
            elif isinstance(content, dict):
                sample = content
                record_count = 1
                for value in content.values():
                    if isinstance(value, str) and value not in sample_values:
                        sample_values.append(value)
            else:
                logger.warning(f"Schema 跳过非对象/数组 JSON: {rel_path}")
                continue

            fields = list(sample.keys()) if isinstance(sample, dict) else []
            locate_by = "name" if "name" in fields else "id" if "id" in fields else ""
            if not locate_by:
                for key, value in sample.items():
                    if isinstance(value, str):
                        locate_by = key
                        break

            schema = {
                "file_path": rel_path,
                "fields": fields,
                "sample_record": sample,
                "sample_values": sample_values,
                "locate_by": locate_by,
                "record_count": record_count,
            }
            output_path = schema_dir / Path(rel_path).name
            output_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"Schema 已生成: {output_path.name}")

    def detect_genre(self, scripts: list[dict]) -> str:
        tokens: list[str] = []
        for script in scripts:
            if script.get("class_name"):
                tokens.append(script["class_name"])
            tokens.extend(field["name"] for field in script.get("public_fields", []))
            tokens.extend(method["name"] for method in script.get("public_methods", []))
            tokens.extend(script.get("unity_methods", []))

        token_text = " ".join(tokens).lower()
        scores = {genre: 0 for genre in GENRE_KEYWORDS}

        for genre, keywords in GENRE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in token_text:
                    scores[genre] += 1

        best_genre = max(scores, key=scores.get) if scores else "unknown"
        logger.info(f"游戏类型检测: {best_genre} | scores={scores}")
        if scores.get(best_genre, 0) >= 2:
            return best_genre
        return "unknown"

    def get_recommended_skills(self, ctx: ProjectContext) -> list[dict]:
        recommendations: list[dict] = []

        if ctx.total_scripts > 0:
            recommendations.append(
                {"skill": "review_code", "label": "🔍 代码审查", "reason": f"{ctx.total_scripts} 个脚本可审查"}
            )

        if ctx.config_files:
            recommendations.append(
                {
                    "skill": "modify_config",
                    "label": "📊 配置修改",
                    "reason": f"发现 {len(ctx.config_files)} 个配置文件",
                }
            )

        has_update = any(
            any(name in ("Update", "FixedUpdate") for name in script.get("unity_methods", []))
            for script in ctx.scripts
        )
        if has_update:
            recommendations.append(
                {"skill": "analyze_perf", "label": "⚡ 性能分析", "reason": "检测到 Update 方法"}
            )

        if ctx.detected_genre != "unknown":
            genre_dir = Path(__file__).resolve().parents[1] / "context" / "skills" / ctx.detected_genre
            genre_skills = sorted(genre_dir.glob("*.md")) if genre_dir.exists() else []
            if genre_skills:
                recommendations.append(
                    {
                        "skill": genre_skills[0].stem,
                        "label": f"🎮 {genre_skills[0].stem}",
                        "reason": f"检测到 {ctx.detected_genre} 项目",
                    }
                )

        if ctx.localization_files:
            recommendations.append({"skill": "translate", "label": "🌐 本地化", "reason": "发现语言文件"})

        uncovered_count = len(ctx.uncovered_scripts)
        if uncovered_count > 0:
            recommendations.append(
                {
                    "skill": "generate_test",
                    "label": "📊 测试覆盖",
                    "reason": f"{uncovered_count} 个脚本未覆盖测试",
                }
            )

        return recommendations[:5]

    def get_script_list(self) -> list[str]:
        if not self._script_list:
            self._scan_scripts()
        return self._script_list

    def get_config_list(self) -> list[str]:
        if not self._config_list:
            self._scan_configs()
        return self._config_list

    def get_shader_list(self) -> list[str]:
        if not self._shader_list:
            self._scan_shaders()
        return self._shader_list

    def get_localization_list(self) -> list[str]:
        if not self._localization_list:
            self._scan_localization()
        return self._localization_list
