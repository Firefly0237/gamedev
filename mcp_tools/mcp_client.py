from __future__ import annotations

import asyncio
import json
import shutil
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from config.logger import logger
from mcp_tools.unity_coplay import get_coplay_stdio_invocation
from scanner.unity_mcp import detect_coplay_package


APP_ROOT = Path(__file__).resolve().parents[1]


class _MCPConnection:
    def __init__(self, name, command, args, cwd=None, env=None):
        self.name = name
        self.command = command
        self.args = args
        self.cwd = cwd
        self.env = env
        self.tool_names: list[str] = []

    async def _with_session(self, callback):
        params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env,
            cwd=self.cwd,
            encoding="utf-8",
            encoding_error_handler="replace",
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                return await callback(session)

    async def _connect(self):
        async def callback(session):
            tools = await session.list_tools()
            return [tool.name for tool in tools.tools]

        self.tool_names = await self._with_session(callback)
        logger.info(f"[{self.name}] 连接成功，工具: {self.tool_names}")

    def connect_sync(self):
        asyncio.run(self._connect())

    def call_sync(self, tool_name, arguments) -> str:
        async def callback(session):
            result = await session.call_tool(tool_name, arguments)
            texts = [block.text for block in result.content if getattr(block, "type", "") == "text"]
            if texts:
                return "\n".join(texts)
            if result.structuredContent is not None:
                return json.dumps(result.structuredContent, ensure_ascii=False, indent=2)
            return ""

        return asyncio.run(self._with_session(callback))

    def disconnect_sync(self):
        self.tool_names = []


ENGINE_TOOL_MAP = {
    "unity": {
        "engine_get_logs": "read_console",
    },
}


class MCPClientManager:
    def __init__(self):
        self._connections: dict[str, _MCPConnection] = {}
        self._tool_registry: dict[str, str] = {}
        self.project_path: str = ""
        self._engine: str = ""
        self._unity_status = {
            "provider": "coplay",
            "transport": "stdio",
            "package_installed": False,
            "package_name": "",
            "connected": False,
            "reason": "",
            "tool_names": [],
        }

    def init(self, project_path, engine="unity"):
        self.shutdown()
        self.project_path = project_path
        self._engine = engine

        npx_path = shutil.which("npx") or shutil.which("npx.cmd")
        if npx_path:
            conn = _MCPConnection(
                "fs",
                npx_path,
                ["-y", "@modelcontextprotocol/server-filesystem", project_path],
            )
            try:
                conn.connect_sync()
                self._connections["fs"] = conn
            except Exception as exc:
                logger.warning(f"[fs] 连接失败: {exc}")
        else:
            logger.warning("[fs] 未找到 npx")

        git_connected = False
        git_attempts = [
            (
                sys.executable,
                ["-m", "mcp_server_git", "--repository", project_path],
            )
        ]
        uvx_path = shutil.which("uvx") or shutil.which("uvx.exe")
        if uvx_path:
            git_attempts.append((uvx_path, ["mcp-server-git", "--repository", project_path]))

        for command, args in git_attempts:
            conn = _MCPConnection("git", command, args)
            try:
                conn.connect_sync()
                self._connections["git"] = conn
                git_connected = True
                break
            except Exception as exc:
                logger.warning(f"[git] 连接尝试失败 ({command}): {exc}")

        if not git_connected:
            logger.warning("[git] 所有连接尝试均失败")

        if engine == "unity":
            self._register_coplay_unity()

        self._tool_registry = {}
        for name, conn in self._connections.items():
            for tool_name in conn.tool_names:
                self._tool_registry[tool_name] = name
        logger.info(f"工具注册: {len(self._tool_registry)} 个")

    def _register_coplay_unity(self):
        package_status = detect_coplay_package(self.project_path)
        self._unity_status = {
            "provider": "coplay",
            "transport": "stdio",
            "package_installed": package_status["package_installed"],
            "package_name": package_status["package_name"],
            "connected": False,
            "reason": package_status["reason"],
            "tool_names": [],
        }

        if not package_status["is_unity_project"]:
            logger.info("[unity_coplay] 非 Unity 项目，跳过")
            return

        if not package_status["package_installed"]:
            logger.warning(
                f"[unity_coplay] 项目未安装 {package_status['package_name']}，Unity 编译/测试将降级为不可用"
            )
            return

        command, args, env = get_coplay_stdio_invocation()
        if not command:
            self._unity_status["reason"] = "未找到 uv/uvx"
            logger.warning("[unity_coplay] 未找到 uv/uvx，跳过 Unity MCP Server 注册")
            return

        try:
            conn = _MCPConnection(
                "unity_coplay",
                command,
                args,
                cwd=self.project_path,
                env=env,
            )
            conn.connect_sync()
            self._connections["unity_coplay"] = conn
            self._unity_status["connected"] = True
            self._unity_status["reason"] = ""
            self._unity_status["tool_names"] = list(conn.tool_names)
            logger.info(f"[unity_coplay] 已注册 {len(conn.tool_names)} 个工具")
        except Exception as exc:
            self._unity_status["reason"] = str(exc)
            logger.warning(f"[unity_coplay] 连接失败: {exc}")
            logger.warning("Unity 编译/测试将降级为不可用")

    def call_tool(self, tool_name, arguments) -> str:
        arguments = dict(arguments or {})
        actual_name = tool_name

        alias_map = {
            "git_diff_unified": "git_diff_unstaged",
        }
        actual_name = alias_map.get(actual_name, actual_name)

        if tool_name.startswith("engine_"):
            engine_map = ENGINE_TOOL_MAP.get(self._engine, {})
            if tool_name not in engine_map:
                raise RuntimeError(f"未定义引擎工具映射: {tool_name}")
            actual_name = engine_map[tool_name]

        if actual_name.startswith("git_") and "repo_path" not in arguments:
            arguments["repo_path"] = self.project_path

        if actual_name == "git_log" and "count" in arguments and "max_count" not in arguments:
            arguments["max_count"] = arguments.pop("count")

        server_name = self._tool_registry.get(actual_name)
        if not server_name:
            available = ", ".join(sorted(self._tool_registry.keys()))
            raise RuntimeError(f"未找到工具: {actual_name} | 已注册工具: {available}")

        logger.debug(
            f"MCP 调用: {server_name}.{actual_name}({json.dumps(arguments, ensure_ascii=False)[:200]})"
        )
        return self._connections[server_name].call_sync(actual_name, arguments)

    def is_connected(self, server=None) -> bool:
        if server:
            return server in self._connections
        return bool(self._connections)

    def get_status(self) -> dict[str, bool]:
        return {name: True for name in self._connections.keys()}

    def get_all_tools(self) -> list[str]:
        return sorted(self._tool_registry.keys())

    def get_unity_status(self) -> dict:
        return dict(self._unity_status)

    def shutdown(self):
        for conn in list(self._connections.values()):
            conn.disconnect_sync()
        self._connections.clear()
        self._tool_registry.clear()
        self.project_path = ""
        self._engine = ""
        self._unity_status = {
            "provider": "coplay",
            "transport": "stdio",
            "package_installed": False,
            "package_name": "",
            "connected": False,
            "reason": "",
            "tool_names": [],
        }


_manager = MCPClientManager()


def init_mcp(project_path, engine="unity"):
    _manager.init(project_path, engine)


def call_mcp_tool(tool_name, arguments):
    return _manager.call_tool(tool_name, arguments)


def is_mcp_connected(server=None):
    return _manager.is_connected(server)


def get_mcp_status():
    return _manager.get_status()


def get_all_mcp_tools():
    return _manager.get_all_tools()


def get_project_path():
    return _manager.project_path


def get_unity_status():
    return _manager.get_unity_status()


def shutdown_mcp():
    _manager.shutdown()
