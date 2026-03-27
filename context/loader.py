from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config.settings import get_settings


class ContextLoader:
    def __init__(self) -> None:
        self.settings = get_settings()

    def load_pattern(self, pattern_name: str) -> dict[str, Any]:
        path = self.settings.patterns_dir / f"{pattern_name}.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def list_patterns(self) -> list[str]:
        return sorted(path.stem for path in self.settings.patterns_dir.glob("*.json"))

    def list_project_schemas(self) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for path in sorted(self.settings.project_schema_dir.glob("*.json")):
            payload.append(json.loads(path.read_text(encoding="utf-8")))
        return payload

    def match_project_schema(self, target_hint: str = "") -> dict[str, Any] | None:
        hint = target_hint.lower().strip()
        schemas = self.list_project_schemas()
        if not hint:
            return schemas[0] if schemas else None
        for schema in schemas:
            if hint in schema.get("schema_name", "").lower():
                return schema
            if hint in schema.get("file_path", "").lower():
                return schema
        return schemas[0] if schemas else None

    def build_context_layers(
        self,
        project_context: dict[str, Any] | None,
        pattern_name: str | None,
        target_hint: str = "",
    ) -> dict[str, Any]:
        pattern = self.load_pattern(pattern_name) if pattern_name else {}
        schema = self.match_project_schema(target_hint)
        return {
            "project_overview": project_context or {},
            "pattern": pattern,
            "project_schema": schema or {},
        }


def truncate_text_file(path: Path, limit: int = 4000) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")[:limit]
