import json
import os
import re
from pathlib import Path

from config.logger import logger
from scanner.base import BaseScanner, ProjectContext


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

    def validate_project(self) -> tuple[bool, str]:
        if not (self.project_root / "ProjectSettings").exists():
            return False, "缺少 ProjectSettings/"
        if not self.assets_root.exists():
            return False, "缺少 Assets/"
        if not (self.project_root / "ProjectSettings" / "ProjectVersion.txt").exists():
            return False, "缺少 ProjectSettings/ProjectVersion.txt"
        return True, ""

    def scan(self) -> ProjectContext:
        scripts = self._scan_scripts()
        scenes = self._scan_scenes()
        prefabs = self._scan_assets()
        configs = self._scan_configs()
        shaders = self._scan_shaders()
        localization = self._scan_localization()

        self._auto_generate_schemas(configs)
        detected_genre = self.detect_genre(scripts)

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
        )
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

    def _scan_scripts(self) -> list[dict]:
        scripts: list[dict] = []
        self._script_list = []

        for path in sorted(self.assets_root.rglob("*.cs")):
            if "Plugins" in path.parts:
                continue
            rel_path = self._relpath(path)
            content = path.read_text(encoding="utf-8", errors="ignore")
            scripts.append(self._parse_csharp(content, rel_path))
            self._script_list.append(rel_path)

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
