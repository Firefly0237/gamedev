from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool


server = Server("gamedev-tools")
ROOT: Path | None = None

SKIP = ["Library/", "Temp/", "Packages/", "obj/", ".git/"]
SKIP_PARTS = {item.rstrip("/\\").lower() for item in SKIP}
REFERENCE_EXTENSIONS = {".meta", ".asset", ".prefab", ".unity", ".mat", ".controller", ".anim"}
TEXTURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tga", ".psd", ".bmp"}
MAX_REFERENCE_RESULTS = 30
MAX_TEXTURE_RESULTS = 50
MAX_SETTINGS_CHARS = 5000
SERVER_VERSION = "0.1.0"


def _safe_resolve(rel: str) -> Path | None:
    if ROOT is None:
        return None

    clean_rel = (rel or "").strip()
    if not clean_rel:
        return None
    candidate_input = Path(clean_rel)

    if candidate_input.is_absolute():
        candidate = candidate_input.resolve()
    else:
        candidate = (ROOT / candidate_input).resolve()

    try:
        candidate.relative_to(ROOT)
    except ValueError:
        return None
    return candidate


def _is_skipped(path: Path) -> bool:
    if ROOT is None:
        return False

    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        return True

    return any(part.lower() in SKIP_PARTS for part in relative.parts)


def _text_result(text: str) -> list[TextContent]:
    return [TextContent(type="text", text=text)]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _format_mb(size_bytes: int) -> str:
    return f"{size_bytes / (1024 * 1024):.2f}"


def _format_kb(size_bytes: int) -> str:
    return f"{size_bytes / 1024:.1f}"


def _project_relative(path: Path) -> str:
    if ROOT is None:
        return path.as_posix()
    return path.relative_to(ROOT).as_posix()


def _iter_files(base: Path):
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        if _is_skipped(path):
            continue
        yield path


def _require_string(arguments: dict, key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing required argument: {key}")
    return value.strip()


def _optional_string(arguments: dict, key: str, default: str) -> str:
    value = arguments.get(key, default)
    if not isinstance(value, str) or not value.strip():
        return default
    return value.strip()


def _parse_meta_file(arguments: dict) -> str:
    relative_path = _require_string(arguments, "relative_path")
    meta_relative_path = relative_path if relative_path.endswith(".meta") else f"{relative_path}.meta"
    meta_path = _safe_resolve(meta_relative_path)
    if meta_path is None:
        return f"Path outside project root: {meta_relative_path}"
    if not meta_path.exists():
        return f"Meta file not found: {meta_relative_path}"

    content = _read_text(meta_path)
    guid_match = re.search(r"(?m)^\s*guid:\s*([^\s]+)", content)
    guid = guid_match.group(1) if guid_match else "NOT_FOUND"

    preview_lines: list[str] = []
    for line in content.splitlines():
        if line.strip().startswith("guid:"):
            continue
        preview_lines.append(line)
        if len(preview_lines) >= 10:
            break

    display_name = Path(relative_path).name.replace(".meta", "")
    lines = [
        f"File: {display_name}",
        f"Path: {_project_relative(meta_path)}",
        f"GUID: {guid}",
        "Import settings preview:",
        *(preview_lines or ["<empty>"]),
    ]
    return "\n".join(lines)


def _find_references(arguments: dict) -> str:
    if ROOT is None:
        return "Project root is not initialized."

    guid = _require_string(arguments, "guid")
    matches: list[str] = []
    truncated = False

    for path in _iter_files(ROOT):
        if path.suffix.lower() not in REFERENCE_EXTENSIONS:
            continue
        try:
            if guid in _read_text(path):
                matches.append(_project_relative(path))
                if len(matches) >= MAX_REFERENCE_RESULTS:
                    truncated = True
                    break
        except OSError:
            continue

    if not matches:
        return f"No references found for GUID: {guid}"

    lines = [
        f"GUID: {guid}",
        f"Matched files: {len(matches)}",
        *[f"- {match}" for match in matches],
    ]
    if truncated:
        lines.append(f"... truncated to first {MAX_REFERENCE_RESULTS} results")
    return "\n".join(lines)


def _scan_asset_sizes(arguments: dict) -> str:
    relative_path = _optional_string(arguments, "relative_path", "Assets")
    base_path = _safe_resolve(relative_path)
    if base_path is None:
        return f"Path outside project root: {relative_path}"
    if not base_path.exists():
        return f"Directory not found: {relative_path}"
    if not base_path.is_dir():
        return f"Path is not a directory: {relative_path}"

    stats: dict[str, dict[str, int]] = {}
    total_files = 0
    for path in _iter_files(base_path):
        extension = path.suffix.lower() or "[no_ext]"
        bucket = stats.setdefault(extension, {"count": 0, "total_bytes": 0})
        size = path.stat().st_size
        bucket["count"] += 1
        bucket["total_bytes"] += size
        total_files += 1

    if not stats:
        return f"No files found under: {relative_path}"

    rows = sorted(stats.items(), key=lambda item: item[1]["total_bytes"], reverse=True)
    lines = [
        f"Directory: {relative_path}",
        f"Total files: {total_files}",
        "",
        "Extension | Count | SizeMB",
        "--------- | ----- | ------",
    ]
    for extension, data in rows:
        lines.append(f"{extension} | {data['count']} | {_format_mb(data['total_bytes'])}")
    return "\n".join(lines)


def _scan_texture_info(arguments: dict) -> str:
    relative_path = _optional_string(arguments, "relative_path", "Assets")
    base_path = _safe_resolve(relative_path)
    if base_path is None:
        return f"Path outside project root: {relative_path}"
    if not base_path.exists():
        return f"Directory not found: {relative_path}"
    if not base_path.is_dir():
        return f"Path is not a directory: {relative_path}"

    textures: list[tuple[int, str, str]] = []
    for path in _iter_files(base_path):
        if path.suffix.lower() not in TEXTURE_EXTENSIONS:
            continue
        size = path.stat().st_size
        marker = ""
        if size > 4 * 1024 * 1024:
            marker = "⚠️ 超大"
        elif size > 1 * 1024 * 1024:
            marker = "⚠️ 较大"
        textures.append((size, _project_relative(path), marker))

    if not textures:
        return f"No texture files found under: {relative_path}"

    textures.sort(key=lambda item: item[0], reverse=True)
    lines = [
        f"Directory: {relative_path}",
        f"Texture files: {len(textures)}",
    ]
    for size, rel_path, marker in textures[:MAX_TEXTURE_RESULTS]:
        suffix = f" | {marker}" if marker else ""
        lines.append(f"- {rel_path} | {_format_kb(size)} KB{suffix}")
    if len(textures) > MAX_TEXTURE_RESULTS:
        lines.append(f"... truncated to first {MAX_TEXTURE_RESULTS} textures")
    return "\n".join(lines)


def _read_project_settings(arguments: dict) -> str:
    if ROOT is None:
        return "Project root is not initialized."

    settings_file = _require_string(arguments, "settings_file")
    settings_path = _safe_resolve(str(Path("ProjectSettings") / settings_file))
    project_settings_root = _safe_resolve("ProjectSettings")
    if project_settings_root is None or not project_settings_root.exists():
        return "ProjectSettings directory not found."

    if settings_path is None or not settings_path.exists():
        available_files = sorted(
            _project_relative(path)[len("ProjectSettings/") :]
            for path in project_settings_root.rglob("*")
            if path.is_file()
        )
        payload = json.dumps({"available_files": available_files}, ensure_ascii=False, indent=2)
        return f"Settings file not found: {settings_file}\nAvailable files:\n{payload}"

    content = _read_text(settings_path)
    original_length = len(content)
    if len(content) > MAX_SETTINGS_CHARS:
        content = content[:MAX_SETTINGS_CHARS] + "\n... (truncated)"

    return "\n".join(
        [
            f"File: {_project_relative(settings_path)}",
            f"Length: {original_length}",
            "",
            content,
        ]
    )


TOOLS = [
    Tool(
        name="parse_meta_file",
        description="解析 Unity .meta 文件，获取资源的 GUID 和导入设置",
        inputSchema={
            "type": "object",
            "properties": {
                "relative_path": {
                    "type": "string",
                    "description": "Relative asset path, for example Assets/Prefabs/Characters/Player.prefab",
                }
            },
            "required": ["relative_path"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="find_references",
        description="搜索项目中哪些文件引用了指定的 GUID",
        inputSchema={
            "type": "object",
            "properties": {
                "guid": {
                    "type": "string",
                    "description": "Unity asset GUID to search for",
                }
            },
            "required": ["guid"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="scan_asset_sizes",
        description="统计指定目录下各类资源文件的数量和总大小，按扩展名分类",
        inputSchema={
            "type": "object",
            "properties": {
                "relative_path": {
                    "type": "string",
                    "default": "Assets",
                    "description": "Relative directory path to scan",
                }
            },
            "additionalProperties": False,
        },
    ),
    Tool(
        name="scan_texture_info",
        description="扫描目录下的纹理文件，报告大小，标记过大文件",
        inputSchema={
            "type": "object",
            "properties": {
                "relative_path": {
                    "type": "string",
                    "default": "Assets",
                    "description": "Relative directory path to scan",
                }
            },
            "additionalProperties": False,
        },
    ),
    Tool(
        name="read_project_settings",
        description="读取 Unity ProjectSettings 目录下的配置文件",
        inputSchema={
            "type": "object",
            "properties": {
                "settings_file": {
                    "type": "string",
                    "description": "File name under ProjectSettings/",
                }
            },
            "required": ["settings_file"],
            "additionalProperties": False,
        },
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handlers = {
        "parse_meta_file": _parse_meta_file,
        "find_references": _find_references,
        "scan_asset_sizes": _scan_asset_sizes,
        "scan_texture_info": _scan_texture_info,
        "read_project_settings": _read_project_settings,
    }
    handler = handlers.get(name)
    if handler is None:
        raise ValueError(f"Unknown tool: {name}")
    return _text_result(handler(arguments))


async def main():
    global ROOT

    if len(sys.argv) < 2:
        print("Usage: python -m mcp_tools.mcp_server_gamedev <project_path>", file=sys.stderr)
        raise SystemExit(1)

    project_path = Path(sys.argv[1]).expanduser().resolve()
    if not project_path.exists():
        print(f"Project path does not exist: {project_path}", file=sys.stderr)
        raise SystemExit(1)

    ROOT = project_path
    print(f"[gamedev-tools] started for project: {ROOT}", file=sys.stderr)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=server.name,
                server_version=SERVER_VERSION,
                capabilities=server.get_capabilities(
                    NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
