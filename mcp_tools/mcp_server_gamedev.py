from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool


server = Server("gamedev-tools")
ROOT: Path | None = None
SKIP_NAMES = {"Library", "Temp", "Packages", "obj", ".git"}


def _safe_resolve(rel: str) -> Path | None:
    if ROOT is None:
        return None

    base = ROOT.resolve()
    target = (base / rel).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        return None
    return target


def _skip_path(path: Path) -> bool:
    return any(part in SKIP_NAMES for part in path.parts)


def _text_result(text: str) -> list[TextContent]:
    return [TextContent(type="text", text=text)]


def _build_tools() -> list[Tool]:
    return [
        Tool(
            name="parse_meta_file",
            description="解析 Unity .meta 文件，获取 GUID 和导入设置",
            inputSchema={
                "type": "object",
                "properties": {"relative_path": {"type": "string"}},
                "required": ["relative_path"],
            },
        ),
        Tool(
            name="find_references",
            description="搜索项目中哪些文件引用了指定 GUID",
            inputSchema={
                "type": "object",
                "properties": {"guid": {"type": "string"}},
                "required": ["guid"],
            },
        ),
        Tool(
            name="scan_asset_sizes",
            description="按扩展名统计资源文件数量和大小",
            inputSchema={
                "type": "object",
                "properties": {"relative_path": {"type": "string", "default": "Assets"}},
            },
        ),
        Tool(
            name="scan_texture_info",
            description="扫描纹理文件，标记过大文件",
            inputSchema={
                "type": "object",
                "properties": {"relative_path": {"type": "string", "default": "Assets"}},
            },
        ),
        Tool(
            name="read_project_settings",
            description="读取 ProjectSettings 目录下的配置文件",
            inputSchema={
                "type": "object",
                "properties": {"settings_file": {"type": "string"}},
                "required": ["settings_file"],
            },
        ),
        Tool(
            name="validate_all_configs",
            description="校验项目所有配置文件的字段类型、ID 重复、数值范围等常见问题",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


def _parse_meta_file(arguments: dict) -> list[TextContent]:
    rel = arguments["relative_path"]
    meta_rel = rel if rel.endswith(".meta") else f"{rel}.meta"
    path = _safe_resolve(meta_rel)
    if path is None or not path.exists():
        return _text_result(f"未找到 meta 文件: {meta_rel}")

    content = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"guid:\s*([a-f0-9]+)", content)
    guid = match.group(1) if match else "unknown"
    text = f"文件: {meta_rel}\nGUID: {guid}"
    return _text_result(text)


def _find_references(arguments: dict) -> list[TextContent]:
    guid = arguments["guid"]
    results: list[str] = []
    exts = {".meta", ".asset", ".prefab", ".unity", ".mat", ".controller", ".anim"}

    for path in ROOT.rglob("*"):  # type: ignore[union-attr]
        if not path.is_file() or _skip_path(path) or path.suffix.lower() not in exts:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if guid in content:
            results.append(str(path.relative_to(ROOT)))  # type: ignore[arg-type]
            if len(results) >= 30:
                break

    if not results:
        return _text_result(f"未找到对 GUID {guid} 的引用")

    lines = [f"GUID: {guid}", f"引用数: {len(results)}"] + [f"- {item}" for item in results]
    return _text_result("\n".join(lines))


def _scan_asset_sizes(arguments: dict) -> list[TextContent]:
    rel = arguments.get("relative_path", "Assets")
    path = _safe_resolve(rel)
    if path is None or not path.exists():
        return _text_result(f"目录不存在: {rel}")

    stats: dict[str, dict[str, float]] = {}
    for file_path in path.rglob("*"):
        if not file_path.is_file() or _skip_path(file_path):
            continue
        ext = file_path.suffix.lower() or "[no_ext]"
        entry = stats.setdefault(ext, {"count": 0, "size": 0.0})
        entry["count"] += 1
        entry["size"] += file_path.stat().st_size

    lines = ["扩展名 | 数量 | 大小MB"]
    for ext, data in sorted(stats.items(), key=lambda item: item[1]["size"], reverse=True):
        size_mb = data["size"] / (1024 * 1024)
        lines.append(f"{ext} | {int(data['count'])} | {size_mb:.2f}")
    return _text_result("\n".join(lines))


def _scan_texture_info(arguments: dict) -> list[TextContent]:
    rel = arguments.get("relative_path", "Assets")
    path = _safe_resolve(rel)
    if path is None or not path.exists():
        return _text_result(f"目录不存在: {rel}")

    texture_exts = {".png", ".jpg", ".jpeg", ".tga", ".psd", ".bmp"}
    lines = []
    count = 0
    for file_path in sorted(path.rglob("*")):
        if not file_path.is_file() or _skip_path(file_path):
            continue
        if file_path.suffix.lower() not in texture_exts:
            continue

        size_mb = file_path.stat().st_size / (1024 * 1024)
        flag = ""
        if size_mb > 4:
            flag = " ⚠️ 超大"
        elif size_mb > 1:
            flag = " ⚠️ 较大"

        lines.append(f"{file_path.relative_to(ROOT)} | {size_mb:.2f} MB{flag}")  # type: ignore[arg-type]
        count += 1
        if count >= 50:
            break

    return _text_result("\n".join(lines) if lines else "未发现纹理文件")


def _read_project_settings(arguments: dict) -> list[TextContent]:
    settings_file = arguments["settings_file"]
    path = _safe_resolve(f"ProjectSettings/{settings_file}")
    settings_dir = _safe_resolve("ProjectSettings")
    if settings_dir is None or not settings_dir.exists():
        return _text_result("ProjectSettings 目录不存在")

    if path is None or not path.exists():
        files = sorted(item.name for item in settings_dir.iterdir() if item.is_file())
        return _text_result(f"文件不存在: {settings_file}\n可用文件:\n- " + "\n- ".join(files))

    content = path.read_text(encoding="utf-8", errors="ignore")
    return _text_result(content[:5000])


def _validate_all_configs(arguments: dict) -> list[TextContent]:
    _ = arguments
    project_root = ROOT
    if project_root is None:
        return _text_result("项目根目录未初始化")

    project_dir = Path(__file__).resolve().parents[1]
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))

    from graphs.validators import validate_all_configs

    schemas = []
    schema_dir = project_dir / "context" / "project_schemas"
    if schema_dir.exists():
        for file_path in schema_dir.glob("*.json"):
            try:
                schemas.append(json.loads(file_path.read_text(encoding="utf-8")))
            except Exception:
                continue

    result = validate_all_configs(str(project_root), schemas)
    return _text_result(json.dumps(result, ensure_ascii=False, indent=2))


@server.list_tools()
async def list_tools():
    return _build_tools()


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "parse_meta_file":
        return _parse_meta_file(arguments)
    if name == "find_references":
        return _find_references(arguments)
    if name == "scan_asset_sizes":
        return _scan_asset_sizes(arguments)
    if name == "scan_texture_info":
        return _scan_texture_info(arguments)
    if name == "read_project_settings":
        return _read_project_settings(arguments)
    if name == "validate_all_configs":
        return _validate_all_configs(arguments)
    return _text_result(f"未知工具: {name}")


async def main():
    global ROOT

    if len(sys.argv) < 2:
        raise SystemExit(1)

    ROOT = Path(sys.argv[1]).resolve()
    if not ROOT.exists():
        raise SystemExit(1)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
