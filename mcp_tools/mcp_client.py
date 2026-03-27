from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from config.settings import MCPServerConfig, get_settings
from mcp_tools.mcp_server_gamedev import get_tool_registry


ToolCallable = Callable[..., Any]


@dataclass(slots=True)
class LocalConnection:
    name: str
    server_type: str
    tools: dict[str, ToolCallable] = field(default_factory=dict)

    @property
    def tool_names(self) -> list[str]:
        return list(self.tools.keys())

    def call_sync(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name not in self.tools:
            raise KeyError(f"Tool {tool_name} is not registered on server {self.name}.")
        return self.tools[tool_name](**arguments)


class MCPClientManager:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._connections: dict[str, LocalConnection] = {}
        self._tool_registry: dict[str, str] = {}
        self._engine_type = "generic"
        self._register_builtin_servers()

    def _register_builtin_servers(self) -> None:
        for server in self.settings.mcp_servers:
            if server.name == "gamedev":
                self.register_connection(
                    LocalConnection(
                        name=server.name,
                        server_type=server.server_type,
                        tools=get_tool_registry(),
                    )
                )
            else:
                self.register_connection(LocalConnection(name=server.name, server_type=server.server_type, tools={}))

    def register_connection(self, connection: LocalConnection) -> None:
        self._connections[connection.name] = connection
        for tool_name in connection.tool_names:
            self._tool_registry[tool_name] = connection.name
        if connection.server_type in self.settings.engine_tool_aliases:
            self._engine_type = connection.server_type

    def register_placeholder_tool(self, server_name: str, tool_name: str) -> None:
        connection = self._connections.setdefault(server_name, LocalConnection(name=server_name, server_type="generic"))
        if tool_name not in connection.tools:
            connection.tools[tool_name] = lambda **_: {
                "status": "offline",
                "message": f"{server_name}:{tool_name} is not wired yet.",
            }
            self._tool_registry[tool_name] = server_name

    def list_tools(self) -> dict[str, list[str]]:
        return {name: connection.tool_names for name, connection in self._connections.items()}

    def resolve_tool_name(self, tool_name: str) -> str:
        aliases = self.settings.engine_tool_aliases.get(self._engine_type, {})
        return aliases.get(tool_name, tool_name)

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        actual_name = self.resolve_tool_name(tool_name)
        target = self._tool_registry.get(actual_name)
        if target is None:
            raise KeyError(f"Tool {tool_name} (resolved as {actual_name}) is not registered.")
        return self._connections[target].call_sync(actual_name, arguments)

    def load_default_placeholders(self) -> None:
        for server, tools in {
            "filesystem": ["read_file", "write_file", "list_directory", "search_files"],
            "git": ["git_status", "git_diff_unified", "git_log", "git_add", "git_commit"],
            "unity": ["unity_execute", "unity_compile", "unity_scene_hierarchy", "unity_screenshot"],
        }.items():
            for tool_name in tools:
                self.register_placeholder_tool(server, tool_name)
