import asyncio
import json
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool


sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_tools.unity_cli import get_unity_logs, run_unity_compile, run_unity_tests


server = Server("unity-tools")
ROOT: Path | None = None

TOOLS = [
    Tool(
        name="unity_compile",
        description="触发 Unity headless 编译当前项目，返回错误和警告列表。需要本地安装 Unity 并配置 UNITY_EXECUTABLE_PATH。",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="unity_run_tests",
        description="运行 Unity NUnit 测试（EditMode），返回 passed/failed/skipped 统计和失败详情。",
        inputSchema={
            "type": "object",
            "properties": {
                "test_filter": {
                    "type": "string",
                    "description": "可选的测试过滤器（NUnit 名称匹配，如 'PlayerControllerTests'）",
                }
            },
        },
    ),
    Tool(
        name="unity_get_logs",
        description="读取系统 Unity Editor.log 最近 N 行（用于查看上次手动编译/运行的输出）",
        inputSchema={
            "type": "object",
            "properties": {
                "lines": {"type": "integer", "default": 100},
            },
        },
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    global ROOT

    if name == "unity_compile":
        result = run_unity_compile(str(ROOT))
        text = json.dumps(result, ensure_ascii=False, indent=2)
        return [TextContent(type="text", text=text)]

    if name == "unity_run_tests":
        test_filter = arguments.get("test_filter", "")
        result = run_unity_tests(str(ROOT), test_filter)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        return [TextContent(type="text", text=text)]

    if name == "unity_get_logs":
        lines = arguments.get("lines", 100)
        text = get_unity_logs(lines)
        return [TextContent(type="text", text=text)]

    return [TextContent(type="text", text=f"未知工具: {name}")]


async def main():
    global ROOT
    if len(sys.argv) < 2:
        print("用法: python -m mcp_tools.mcp_server_unity <project_path>", file=sys.stderr)
        sys.exit(1)

    ROOT = Path(sys.argv[1])
    if not ROOT.exists():
        print(f"项目路径不存在: {ROOT}", file=sys.stderr)
        sys.exit(1)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
