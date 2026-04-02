from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from config.logger import logger
from scanner.base import BaseScanner, ProjectContext


@dataclass
class ScriptInfo:
    path: str
    class_name: str = ""
    base_class: str = ""
    namespace: str = ""
    public_fields: list[dict] = field(default_factory=list)
    public_methods: list[dict] = field(default_factory=list)
    using_statements: list[str] = field(default_factory=list)


class UnityScanner(BaseScanner):
    """Unity 项目扫描器，提取脚本骨架与项目上下文。"""

    RE_NAMESPACE = re.compile(r"^\s*namespace\s+([A-Za-z_][\w.]*)", re.MULTILINE)
    RE_CLASS = re.compile(
        r"^\s*(?:public\s+)?(?:(?:abstract|partial|sealed)\s+)*class\s+"
        r"([A-Za-z_]\w*)(?:\s*:\s*([^{\n]+))?",
        re.MULTILINE,
    )
    RE_FIELD = re.compile(
        r"^\s*(?:\[[^\]]+\]\s*)*public\s+"
        r"(?!class\b|struct\b|enum\b|interface\b|event\b)"
        r"([A-Za-z_][\w<>\[\],.? ]*)\s+([A-Za-z_]\w*)\s*(?:=[^;]*)?;",
        re.MULTILINE,
    )
    RE_METHOD = re.compile(
        r"^\s*public\s+(?:(?:virtual|override|static|async|sealed|extern|new)\s+)*"
        r"([A-Za-z_][\w<>\[\],.? ]*)\s+([A-Za-z_]\w*)\s*\(([^)]*)\)",
        re.MULTILINE,
    )
    RE_USING = re.compile(r"^\s*using\s+([A-Za-z_][\w.]*)\s*;", re.MULTILINE)

    SKIP_DIRS = ["Packages/", "Library/", "Temp/", "obj/", ".git/", "Logs/"]
    CONFIG_EXTENSIONS = {".json", ".xml", ".yaml", ".yml", ".csv"}
    LOCALIZATION_HINTS = ("localization", "i18n", "lang")
    INVALID_FIELD_NAMES = {"get", "set", "value", "if", "else", "return", "new", "this"}

    def __init__(self, project_path: str):
        super().__init__(project_path)
        self.project_path = Path(project_path).resolve()
        self.assets_path = self.project_path / "Assets"
        self.schema_dir = Path(__file__).resolve().parent.parent / "context" / "project_schemas"

    def validate_project(self) -> tuple[bool, str]:
        if not self.project_path.exists():
            return False, "项目路径不存在。"
        if not self.project_path.is_dir():
            return False, "项目路径不是目录。"
        if not self.assets_path.exists():
            return False, "缺少 Assets 目录。"
        if not (self.project_path / "ProjectSettings").exists():
            return False, "缺少 ProjectSettings 目录。"
        return True, "Unity 项目路径有效。"

    def scan(self) -> ProjectContext:
        valid, message = self.validate_project()
        if not valid:
            logger.warning("Unity 项目验证失败 | path=%s | reason=%s", self.project_path, message)
            return ProjectContext(project_path=str(self.project_path), engine="unity")

        scripts: list[dict[str, Any]] = []
        for script_path in sorted(self.project_path.rglob("*.cs")):
            if not script_path.is_file():
                continue
            rel_path = script_path.relative_to(self.project_path).as_posix()
            if self._should_skip(rel_path):
                continue
            content = script_path.read_text(encoding="utf-8", errors="ignore")
            scripts.append(asdict(self._parse_csharp(content, rel_path)))

        scenes = self._scan_ext(".unity")
        prefabs = self._scan_ext(".prefab")
        shader_files = self._scan_ext(".shader")
        config_files = self._scan_configs()
        localization_files = self._scan_localization()

        context = ProjectContext(
            project_path=str(self.project_path),
            engine="unity",
            engine_version=self._read_engine_version(),
            scripts=scripts,
            scenes=scenes,
            assets=self._scan_assets(),
            config_files=config_files,
            localization_files=localization_files,
            shader_files=shader_files,
            prefabs=prefabs,
            directory_tree=self._build_tree(max_depth=3),
            total_scripts=len(scripts),
        )

        self._auto_generate_schemas(config_files)
        logger.info(
            "Unity 扫描完成 | path=%s | version=%s | scripts=%s | scenes=%s | prefabs=%s | shaders=%s | configs=%s | localization=%s",
            context.project_path,
            context.engine_version or "unknown",
            context.total_scripts,
            len(context.scenes),
            len(context.prefabs),
            len(context.shader_files),
            len(context.config_files),
            len(context.localization_files),
        )
        return context

    def _parse_csharp(self, content: str, rel_path: str) -> ScriptInfo:
        namespace_match = self.RE_NAMESPACE.search(content)
        class_match = self.RE_CLASS.search(content)

        class_name = class_match.group(1).strip() if class_match else ""
        base_class = ""
        if class_match and class_match.group(2):
            base_class = class_match.group(2).split(",", 1)[0].strip()

        using_statements: list[str] = []
        for namespace in self.RE_USING.findall(content):
            if namespace not in using_statements:
                using_statements.append(namespace)

        public_fields: list[dict[str, str]] = []
        for field_match in self.RE_FIELD.finditer(content):
            field_type = " ".join(field_match.group(1).split())
            field_name = field_match.group(2)
            if field_name.lower() in self.INVALID_FIELD_NAMES:
                continue
            public_fields.append({"type": field_type, "name": field_name})
            if len(public_fields) >= 20:
                break

        public_methods: list[dict[str, str]] = []
        for method_match in self.RE_METHOD.finditer(content):
            return_type = " ".join(method_match.group(1).split())
            method_name = method_match.group(2)
            params = " ".join(method_match.group(3).split())
            public_methods.append(
                {
                    "return_type": return_type,
                    "name": method_name,
                    "params": params,
                }
            )
            if len(public_methods) >= 15:
                break

        return ScriptInfo(
            path=rel_path,
            class_name=class_name,
            base_class=base_class,
            namespace=namespace_match.group(1).strip() if namespace_match else "",
            public_fields=public_fields,
            public_methods=public_methods,
            using_statements=using_statements,
        )

    def _should_skip(self, relative_path: str) -> bool:
        skip_parts = {item.rstrip("/\\").lower() for item in self.SKIP_DIRS}
        parts = [part.lower() for part in Path(relative_path).parts]
        return any(part in skip_parts for part in parts)

    def _scan_ext(self, extension: str) -> list[str]:
        if not self.assets_path.exists():
            return []

        matched: list[str] = []
        for path in sorted(self.assets_path.rglob(f"*{extension}")):
            if not path.is_file():
                continue
            rel_path = path.relative_to(self.project_path).as_posix()
            if self._should_skip(rel_path):
                continue
            matched.append(rel_path)
        return matched

    def _scan_configs(self) -> list[str]:
        matched: list[str] = []
        for path in sorted(self.project_path.rglob("*")):
            if not path.is_file():
                continue
            rel_path = path.relative_to(self.project_path).as_posix()
            if self._should_skip(rel_path):
                continue
            if path.suffix.lower() in self.CONFIG_EXTENSIONS:
                lower_path = rel_path.lower()
                if path.suffix.lower() == ".json" and any(
                    hint in lower_path for hint in self.LOCALIZATION_HINTS
                ):
                    continue
                matched.append(rel_path)
        return matched

    def _scan_localization(self) -> list[str]:
        if not self.assets_path.exists():
            return []

        matched: list[str] = []
        for path in sorted(self.assets_path.rglob("*.json")):
            if not path.is_file():
                continue
            rel_path = path.relative_to(self.project_path).as_posix()
            if self._should_skip(rel_path):
                continue
            lower_path = rel_path.lower()
            if any(hint in lower_path for hint in self.LOCALIZATION_HINTS):
                matched.append(rel_path)
        return matched

    def _build_tree(self, max_depth: int = 3) -> str:
        if not self.assets_path.exists():
            return ""

        lines = ["Assets/"]
        max_lines = 80
        truncated = False

        def walk(directory: Path) -> None:
            nonlocal truncated
            if truncated:
                return

            entries = sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
            for entry in entries:
                if entry.name.startswith("."):
                    continue
                rel_path = entry.relative_to(self.project_path).as_posix()
                if self._should_skip(rel_path):
                    continue

                depth = len(entry.relative_to(self.assets_path).parts)
                if depth > max_depth:
                    continue
                if len(lines) >= max_lines - 1:
                    truncated = True
                    return

                suffix = "/" if entry.is_dir() else ""
                indent = "  " * depth
                lines.append(f"{indent}- {entry.name}{suffix}")

                if entry.is_dir() and depth < max_depth:
                    walk(entry)

        walk(self.assets_path)
        if truncated:
            lines.append("... (truncated)")
        return "\n".join(lines)

    def _auto_generate_schemas(self, config_files: list[str] | None = None) -> None:
        self.schema_dir.mkdir(parents=True, exist_ok=True)
        generated_count = 0

        for rel_path in config_files or self._scan_configs():
            if not rel_path.lower().endswith(".json"):
                continue

            file_path = self.project_path / Path(rel_path)
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8", errors="ignore"))
                sample_record, record_count = self._extract_sample_record(payload)
                if sample_record is None:
                    logger.warning("Schema 跳过空 JSON | path=%s", rel_path)
                    continue

                if not isinstance(sample_record, dict):
                    sample_record = {"value": sample_record}

                fields = list(sample_record.keys())
                if "name" in fields:
                    locate_by = "name"
                elif "id" in fields:
                    locate_by = "id"
                else:
                    locate_by = fields[0] if fields else ""

                schema = {
                    "file_path": rel_path,
                    "type": "json_config",
                    "fields": fields,
                    "sample_record": sample_record,
                    "locate_by": locate_by,
                    "record_count": record_count,
                }

                schema_path = self.schema_dir / f"{Path(rel_path).stem}.json"
                schema_path.write_text(
                    json.dumps(schema, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                generated_count += 1
            except Exception as exc:
                logger.warning("Schema 生成失败 | path=%s | error=%s", rel_path, exc)

        logger.info("Project Schema 自动生成完成 | count=%s", generated_count)

    def get_script_list(self) -> list[str]:
        if not self.project_path.exists():
            return []

        matched: list[str] = []
        for path in sorted(self.project_path.rglob("*.cs")):
            if not path.is_file():
                continue
            rel_path = path.relative_to(self.project_path).as_posix()
            if self._should_skip(rel_path):
                continue
            matched.append(rel_path)
        return matched

    def get_shader_list(self) -> list[str]:
        return self._scan_ext(".shader")

    def get_config_list(self) -> list[str]:
        return self._scan_configs()

    def get_localization_list(self) -> list[str]:
        return self._scan_localization()

    def _read_engine_version(self) -> str:
        version_file = self.project_path / "ProjectSettings" / "ProjectVersion.txt"
        if not version_file.exists():
            return ""

        for line in version_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("m_EditorVersion:"):
                return line.split(":", 1)[1].strip()
        return ""

    def _scan_assets(self) -> list[str]:
        if not self.assets_path.exists():
            return []

        excluded_extensions = {
            ".cs",
            ".meta",
            ".unity",
            ".prefab",
            ".shader",
            ".json",
            ".xml",
            ".yaml",
            ".yml",
            ".csv",
        }
        assets: list[str] = []
        for path in sorted(self.assets_path.rglob("*")):
            if not path.is_file():
                continue
            rel_path = path.relative_to(self.project_path).as_posix()
            if self._should_skip(rel_path):
                continue
            if path.suffix.lower() in excluded_extensions:
                continue
            assets.append(rel_path)
        return assets

    def _extract_sample_record(self, payload: Any) -> tuple[Any | None, int]:
        if isinstance(payload, list):
            if not payload:
                return None, 0
            return payload[0], len(payload)

        if isinstance(payload, dict):
            for value in payload.values():
                if isinstance(value, list) and value:
                    return value[0], len(value)
            if payload:
                return payload, 1
            return None, 0

        return None, 0
