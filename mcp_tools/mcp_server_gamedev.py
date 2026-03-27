from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable


def parse_meta_file(path: str) -> dict[str, Any]:
    file_path = Path(path)
    payload: dict[str, Any] = {"path": str(file_path), "guid": None, "settings": {}}
    if not file_path.exists():
        return payload
    for raw_line in file_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key == "guid":
            payload["guid"] = value
        else:
            payload["settings"][key] = value
    return payload


def find_references(project_root: str, guid: str, limit: int = 100) -> dict[str, Any]:
    root = Path(project_root)
    matches: list[str] = []
    if not root.exists():
        return {"guid": guid, "matches": matches}
    for path in root.rglob("*"):
        if len(matches) >= limit or not path.is_file():
            break
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if guid in content:
            matches.append(str(path.relative_to(root)))
    return {"guid": guid, "matches": matches}


def scan_asset_sizes(project_root: str) -> dict[str, Any]:
    root = Path(project_root)
    distribution: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "bytes": 0})
    if not root.exists():
        return {"project_root": project_root, "distribution": {}}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        ext = path.suffix.lower() or "<no_ext>"
        distribution[ext]["count"] += 1
        distribution[ext]["bytes"] += path.stat().st_size
    return {"project_root": project_root, "distribution": dict(distribution)}


def scan_texture_info(project_root: str) -> dict[str, Any]:
    root = Path(project_root)
    textures: list[dict[str, Any]] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".tga", ".psd"}:
            continue
        textures.append(
            {
                "path": str(path.relative_to(root)),
                "size_bytes": path.stat().st_size,
                "note": "Dimension parsing can be added when Pillow is introduced.",
            }
        )
    return {"project_root": project_root, "textures": textures}


def read_project_settings(project_root: str) -> dict[str, Any]:
    root = Path(project_root)
    settings_dir = root / "ProjectSettings"
    payload: dict[str, Any] = {}
    if not settings_dir.exists():
        return payload
    for path in settings_dir.glob("*.asset"):
        payload[path.name] = path.read_text(encoding="utf-8", errors="ignore")[:4000]
    return payload


def get_tool_registry() -> dict[str, Callable[..., Any]]:
    return {
        "parse_meta_file": parse_meta_file,
        "find_references": find_references,
        "scan_asset_sizes": scan_asset_sizes,
        "scan_texture_info": scan_texture_info,
        "read_project_settings": read_project_settings,
    }


def main() -> None:
    tools = sorted(get_tool_registry().keys())
    print(json.dumps({"server": "gamedev", "tools": tools}, ensure_ascii=False))


if __name__ == "__main__":
    main()
