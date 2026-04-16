from __future__ import annotations

import json
from pathlib import Path

from graphs.validators import validate_all_configs
from scanner.asset_stats import scan_asset_sizes, scan_texture_info
from scanner.project_settings import read_project_settings
from scanner.reference_graph import find_guid_references, parse_meta_file


LOCAL_TOOL_NAMES = {
    "parse_meta_file",
    "find_references",
    "scan_asset_sizes",
    "scan_texture_info",
    "read_project_settings",
    "validate_all_configs",
}


def _schema_list() -> list[dict]:
    schema_dir = Path(__file__).resolve().parents[1] / "context" / "project_schemas"
    schemas = []
    if not schema_dir.exists():
        return schemas

    for file_path in schema_dir.glob("*.json"):
        try:
            schemas.append(json.loads(file_path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return schemas


def execute_local_tool(tool_name: str, arguments: dict, project_path: str) -> str:
    if tool_name == "parse_meta_file":
        result = parse_meta_file(project_path, arguments["relative_path"])
        return json.dumps(result, ensure_ascii=False, indent=2)

    if tool_name == "find_references":
        references = find_guid_references(project_path, arguments["guid"])
        return json.dumps(
            {
                "success": True,
                "guid": arguments["guid"],
                "reference_count": len(references),
                "references": references,
            },
            ensure_ascii=False,
            indent=2,
        )

    if tool_name == "scan_asset_sizes":
        result = scan_asset_sizes(project_path, arguments.get("relative_path", "Assets"))
        return json.dumps(result, ensure_ascii=False, indent=2)

    if tool_name == "scan_texture_info":
        result = scan_texture_info(project_path, arguments.get("relative_path", "Assets"))
        return json.dumps(result, ensure_ascii=False, indent=2)

    if tool_name == "read_project_settings":
        result = read_project_settings(project_path, arguments["settings_file"])
        return json.dumps(result, ensure_ascii=False, indent=2)

    if tool_name == "validate_all_configs":
        result = validate_all_configs(project_path, _schema_list())
        return json.dumps(result, ensure_ascii=False, indent=2)

    raise ValueError(f"未知本地工具: {tool_name}")
