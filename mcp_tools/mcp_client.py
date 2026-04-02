from __future__ import annotations

import asyncio
import importlib.util
import json
import shutil
import sys
import threading
from concurrent.futures import Future
from pathlib import Path

from config.logger import logger
from config.settings import Settings
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ENGINE_TOOL_MAP = {
    "unity": {
        "engine_execute": "unity_execute",
        "engine_scene": "unity_scene_hierarchy",
        "engine_compile": "unity_compile",
        "engine_screenshot": "unity_screenshot",
    },
    # "unreal": { ... }
    # "godot": { ... }
}


class _MCPConnection:
    def __init__(self, name: str, command: str, args: list[str]):
        self.name = name
        self.command = command
        self.args = args
        self.session: ClientSession | None = None
        self.tool_names: list[str] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._shutdown_event: asyncio.Event | None = None
        self._connection_future: Future | None = None
        self._ready_event: threading.Event | None = None
        self._connect_error: Exception | None = None

    async def _list_all_tools(self) -> list[str]:
        if self.session is None:
            return []

        result = await self.session.list_tools()
        tool_names = [tool.name for tool in result.tools]
        cursor = result.nextCursor
        while cursor:
            result = await self.session.list_tools(cursor=cursor)
            tool_names.extend(tool.name for tool in result.tools)
            cursor = result.nextCursor
        return tool_names

    async def _connection_main(self):
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            cwd=str(Settings.PROJECT_ROOT),
            encoding="utf-8",
            encoding_error_handler="ignore",
        )

        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    self.session = session
                    await self.session.initialize()
                    self.tool_names = await self._list_all_tools()
                    logger.info(
                        "MCP Server 已连接 | server=%s | command=%s | tools=%s",
                        self.name,
                        self.command,
                        ", ".join(self.tool_names) or "<none>",
                    )
                    if self._ready_event is not None:
                        self._ready_event.set()
                    if self._shutdown_event is not None:
                        await self._shutdown_event.wait()
        except Exception as exc:
            self._connect_error = exc
            if self._ready_event is not None:
                self._ready_event.set()
        finally:
            self.session = None
            self.tool_names = []

    async def _call(self, tool_name, arguments) -> str:
        if self.session is None:
            raise RuntimeError(f"MCP server '{self.name}' is not connected.")

        result = await self.session.call_tool(tool_name, arguments or {})
        text_blocks = [
            block.text
            for block in result.content
            if getattr(block, "type", None) == "text"
        ]

        if result.isError:
            error_text = "\n".join(text_blocks).strip()
            if not error_text and result.structuredContent is not None:
                error_text = json.dumps(result.structuredContent, ensure_ascii=False, indent=2)
            raise RuntimeError(error_text or f"Tool call failed: {tool_name}")

        if text_blocks:
            return "\n".join(text_blocks).strip()
        if result.structuredContent is not None:
            return json.dumps(result.structuredContent, ensure_ascii=False, indent=2)
        return ""

    async def _disconnect(self):
        if self._shutdown_event is not None:
            self._shutdown_event.set()

    def _stop_loop(self):
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._loop = None
        self._thread = None

    def connect_sync(self):
        if self._loop is not None and self._thread is not None and self._thread.is_alive():
            return

        loop_ready = threading.Event()
        self._ready_event = threading.Event()
        self._connect_error = None

        def _runner():
            loop = asyncio.new_event_loop()
            self._loop = loop
            asyncio.set_event_loop(loop)
            loop_ready.set()
            loop.run_forever()
            loop.close()

        self._thread = threading.Thread(
            target=_runner,
            name=f"mcp-{self.name}",
            daemon=True,
        )
        self._thread.start()

        if not loop_ready.wait(timeout=5):
            self._stop_loop()
            raise RuntimeError(f"Failed to start event loop for MCP server '{self.name}'")

        self._shutdown_event = asyncio.Event()
        self._connection_future = asyncio.run_coroutine_threadsafe(self._connection_main(), self._loop)

        if not self._ready_event.wait(timeout=30):
            try:
                self.disconnect_sync()
            finally:
                raise RuntimeError(f"Timed out connecting MCP server '{self.name}'")

        if self._connect_error is not None:
            error = self._connect_error
            self._stop_loop()
            raise RuntimeError(f"Failed to connect MCP server '{self.name}': {error}") from error

    def call_sync(self, tool_name, arguments) -> str:
        if self._loop is None:
            raise RuntimeError(f"MCP server '{self.name}' is not running.")

        future = asyncio.run_coroutine_threadsafe(self._call(tool_name, arguments), self._loop)
        try:
            return future.result(timeout=60)
        except Exception as exc:
            raise RuntimeError(f"MCP tool call failed | server={self.name} | tool={tool_name} | error={exc}") from exc

    def disconnect_sync(self):
        if self._loop is None:
            self.session = None
            self.tool_names = []
            self._shutdown_event = None
            self._connection_future = None
            self._ready_event = None
            self._connect_error = None
            self._thread = None
            return

        try:
            future = asyncio.run_coroutine_threadsafe(self._disconnect(), self._loop)
            future.result(timeout=10)
            if self._connection_future is not None:
                self._connection_future.result(timeout=10)
        except Exception as exc:
            logger.warning("MCP 断开失败 | server=%s | error=%s", self.name, exc)
        finally:
            self._stop_loop()
            self.session = None
            self.tool_names = []
            self._shutdown_event = None
            self._connection_future = None
            self._ready_event = None
            self._connect_error = None


class MCPClientManager:
    def __init__(self):
        self._connections: dict[str, _MCPConnection] = {}
        self._tool_registry: dict[str, str] = {}
        self.project_path: str = ""
        self._engine: str = ""
        self._status: dict[str, bool] = {}

    def _resolve_command(self, command: str) -> str | None:
        candidates = [command]
        if sys.platform.startswith("win") and "." not in Path(command).name:
            candidates.insert(0, f"{command}.cmd")

        for candidate in candidates:
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
        return None

    def _connect_server(self, name: str, command: str, args: list[str], *, is_critical: bool):
        conn = _MCPConnection(name, command, args)
        try:
            conn.connect_sync()
        except Exception as exc:
            self._status[name] = False
            log_fn = logger.error if is_critical else logger.warning
            log_fn(
                "MCP Server 连接失败 | server=%s | command=%s | args=%s | error=%s",
                name,
                command,
                args,
                exc,
            )
            return

        self._connections[name] = conn
        self._status[name] = True

    def _connect_git_server(self):
        uvx_path = self._resolve_command("uvx")
        if uvx_path:
            self._connect_server(
                "git",
                uvx_path,
                ["mcp-server-git", "--repository", self.project_path],
                is_critical=False,
            )
            if self._status.get("git"):
                return

        if importlib.util.find_spec("mcp_server_git") is not None:
            self._connect_server(
                "git",
                sys.executable,
                ["-m", "mcp_server_git", "--repository", self.project_path],
                is_critical=False,
            )
            return

        self._status["git"] = False
        logger.warning(
            "未找到 Git MCP Server 运行方式，已跳过。请安装 uvx 或执行 `pip install mcp-server-git`。"
        )

    def _rebuild_registry(self):
        self._tool_registry = {}
        for server_name, conn in self._connections.items():
            for tool_name in conn.tool_names:
                if tool_name in self._tool_registry:
                    logger.warning(
                        "MCP 工具名冲突 | tool=%s | previous=%s | current=%s",
                        tool_name,
                        self._tool_registry[tool_name],
                        server_name,
                    )
                self._tool_registry[tool_name] = server_name

        logger.info("MCP 工具注册完成 | count=%s", len(self._tool_registry))
        logger.info("MCP 已连接 Server | servers=%s", sorted(self._connections.keys()))

    def init(self, project_path: str, engine: str = "unity"):
        self.shutdown()

        self.project_path = str(Path(project_path).resolve())
        self._engine = engine
        self._status = {}

        npx_path = self._resolve_command("npx")
        if not npx_path:
            logger.warning("未找到 npx，跳过 FileSystem MCP Server。")
            self._status["fs"] = False
        else:
            self._connect_server(
                "fs",
                npx_path,
                ["-y", "@modelcontextprotocol/server-filesystem", self.project_path],
                is_critical=False,
            )

        self._connect_git_server()

        self._connect_server(
            "gamedev",
            sys.executable,
            ["-m", "mcp_tools.mcp_server_gamedev", self.project_path],
            is_critical=True,
        )

        # 社区 Unity MCP Server 需要 Unity Editor Bridge 先启动，当前先保留接入位。
        self._status.setdefault("unity", False)
        logger.info("Unity MCP Server 已跳过 | reason=requires Unity Editor Bridge")

        self._rebuild_registry()

    def call_tool(self, tool_name: str, arguments: dict) -> str:
        resolved_tool_name = tool_name
        if tool_name.startswith("engine_"):
            engine_map = ENGINE_TOOL_MAP.get(self._engine, {})
            resolved_tool_name = engine_map.get(tool_name, "")
            if not resolved_tool_name:
                raise RuntimeError(
                    f"Engine tool not mapped | engine={self._engine} | tool={tool_name}"
                )

        server_name = self._tool_registry.get(resolved_tool_name)
        if not server_name:
            registered = ", ".join(sorted(self._tool_registry)) or "<none>"
            raise RuntimeError(
                f"Tool not registered: {resolved_tool_name}. Registered tools: {registered}"
            )

        call_arguments = dict(arguments)
        if server_name == "git" and "repo_path" not in call_arguments:
            call_arguments["repo_path"] = self.project_path

        logger.debug(
            "MCP 调用 | request=%s | resolved=%s | server=%s | args=%s",
            tool_name,
            resolved_tool_name,
            server_name,
            call_arguments,
        )
        return self._connections[server_name].call_sync(resolved_tool_name, call_arguments)

    def is_connected(self, server: str = None) -> bool:
        if server is not None:
            return self._status.get(server, False)
        return any(self._status.values())

    def get_status(self) -> dict[str, bool]:
        return dict(self._status)

    def get_all_tools(self) -> list[str]:
        return sorted(self._tool_registry.keys())

    def shutdown(self):
        for server_name, conn in list(self._connections.items()):
            conn.disconnect_sync()
            self._status[server_name] = False

        self._connections = {}
        self._tool_registry = {}


_manager = MCPClientManager()


def init_mcp(project_path: str, engine: str = "unity"):
    _manager.init(project_path, engine)


def call_mcp_tool(tool_name: str, arguments: dict) -> str:
    return _manager.call_tool(tool_name, arguments)


def is_mcp_connected(server: str = None) -> bool:
    return _manager.is_connected(server)


def get_mcp_status() -> dict[str, bool]:
    return _manager.get_status()


def get_all_mcp_tools() -> list[str]:
    return _manager.get_all_tools()


def create_mcp_client(server_url=None) -> MCPClientManager:
    if server_url:
        logger.warning("server_url 参数已忽略，当前使用本地多 Server MCP 架构。")
    return _manager
