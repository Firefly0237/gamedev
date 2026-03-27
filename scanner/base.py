from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ScriptSkeleton:
    name: str
    path: str
    base_class: str | None = None
    public_members: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProjectContext:
    project_root: str
    engine: str
    summary: str
    directory_tree: list[str]
    scripts: list[ScriptSkeleton] = field(default_factory=list)
    scenes: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scripts"] = [asdict(item) for item in self.scripts]
        return data


class BaseScanner(ABC):
    engine_name = "generic"

    @abstractmethod
    def scan_project(self, project_root: Path) -> ProjectContext:
        raise NotImplementedError

    @abstractmethod
    def generate_project_schemas(self, project_root: Path, output_dir: Path) -> list[Path]:
        raise NotImplementedError

    def build_directory_tree(self, project_root: Path, max_depth: int = 3, max_entries: int = 80) -> list[str]:
        lines: list[str] = []
        for path in sorted(project_root.rglob("*")):
            if len(lines) >= max_entries:
                break
            try:
                relative = path.relative_to(project_root)
            except ValueError:
                relative = path
            depth = len(relative.parts) - 1
            if depth > max_depth:
                continue
            prefix = "  " * depth
            suffix = "/" if path.is_dir() else ""
            lines.append(f"{prefix}{relative.name}{suffix}")
        return lines

    def safe_read_text(self, file_path: Path, limit: int = 4000) -> str:
        try:
            return file_path.read_text(encoding="utf-8")[:limit]
        except UnicodeDecodeError:
            return file_path.read_text(encoding="utf-8", errors="ignore")[:limit]
        except OSError:
            return ""

    def write_schema_file(self, output_dir: Path, schema_name: str, payload: dict[str, Any]) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / f"{schema_name}.json"
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return target
