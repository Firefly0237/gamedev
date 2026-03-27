from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scanner.base import BaseScanner, ProjectContext, ScriptSkeleton


CLASS_RE = re.compile(r"class\s+(?P<name>\w+)(?:\s*:\s*(?P<base>[^{]+))?")
PUBLIC_MEMBER_RE = re.compile(r"public\s+[\w<>\[\],?]+\s+(?P<member>\w+)\s*(?:[;({=])")


class UnityScanner(BaseScanner):
    engine_name = "unity"

    def scan_project(self, project_root: Path) -> ProjectContext:
        script_files = self._find_script_files(project_root)
        scene_files = [str(path.relative_to(project_root)) for path in project_root.rglob("*.unity")]
        config_files = [str(path.relative_to(project_root)) for path in project_root.rglob("*.json")]
        scripts = [self._extract_script_skeleton(project_root, path) for path in script_files]
        summary = (
            f"Unity project with {len(scripts)} scripts, "
            f"{len(scene_files)} scenes, {len(config_files)} JSON configs."
        )
        return ProjectContext(
            project_root=str(project_root),
            engine=self.engine_name,
            summary=summary,
            directory_tree=self.build_directory_tree(project_root),
            scripts=scripts,
            scenes=scene_files,
            config_files=config_files,
            metadata={
                "script_count": len(scripts),
                "scene_count": len(scene_files),
                "config_count": len(config_files),
            },
        )

    def generate_project_schemas(self, project_root: Path, output_dir: Path) -> list[Path]:
        generated: list[Path] = []
        for json_file in project_root.rglob("*.json"):
            schema = self._schema_from_json(project_root, json_file)
            if schema is None:
                continue
            generated.append(self.write_schema_file(output_dir, json_file.stem, schema))
        return generated

    def _find_script_files(self, project_root: Path) -> list[Path]:
        asset_scripts = list((project_root / "Assets").rglob("*.cs")) if (project_root / "Assets").exists() else []
        return asset_scripts or list(project_root.rglob("*.cs"))

    def _extract_script_skeleton(self, project_root: Path, path: Path) -> ScriptSkeleton:
        content = self.safe_read_text(path)
        class_match = CLASS_RE.search(content)
        class_name = class_match.group("name") if class_match else path.stem
        base_class = class_match.group("base").strip() if class_match and class_match.group("base") else None
        members = [match.group("member") for match in PUBLIC_MEMBER_RE.finditer(content)][:10]
        return ScriptSkeleton(
            name=class_name,
            path=str(path.relative_to(project_root)),
            base_class=base_class,
            public_members=members,
        )

    def _schema_from_json(self, project_root: Path, file_path: Path) -> dict[str, Any] | None:
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        sample_record: dict[str, Any]
        if isinstance(data, list) and data and isinstance(data[0], dict):
            sample_record = data[0]
        elif isinstance(data, dict):
            sample_record = next((value for value in data.values() if isinstance(value, dict)), data)
        else:
            return None
        fields = list(sample_record.keys())
        locator_field = self._choose_locator_field(fields)
        return {
            "schema_name": file_path.stem,
            "file_path": str(file_path.relative_to(project_root)),
            "locator_field": locator_field,
            "fields": fields,
            "sample_record": sample_record,
        }

    def _choose_locator_field(self, fields: list[str]) -> str | None:
        preferred = ("id", "name", "key", "code")
        lowered = {field.lower(): field for field in fields}
        for candidate in preferred:
            if candidate in lowered:
                return lowered[candidate]
        return fields[0] if fields else None
