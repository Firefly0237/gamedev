from __future__ import annotations

import json
from dataclasses import dataclass

from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import create_react_agent

from agents.llm import create_llm
from config.logger import logger
from graphs.tool_defs import build_tool_definitions
from graphs.safety import normalize_path, safe_write_file
from mcp_tools.mcp_client import call_mcp_tool, get_project_path


MAX_TOOL_TEXT = 12000


@dataclass(frozen=True)
class WorkerSpec:
    name: str
    description: str
    tools: list[str]
    system_prompt: str
    task_type: str = "generation"
    enabled: bool = True
    tool_profile: str = "generate_system"


def _truncate(text: str, limit: int = MAX_TOOL_TEXT) -> str:
    text = str(text or "")
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]..."


def _success(text: str, data: dict | None = None) -> str:
    return json.dumps(
        {
            "status": "success",
            "text": text,
            "data": data or {},
        },
        ensure_ascii=False,
    )


def _error(code: str, message: str, data: dict | None = None) -> str:
    return json.dumps(
        {
            "status": "error",
            "error": {"code": code, "message": message},
            "data": data or {},
        },
        ensure_ascii=False,
    )


def _current_project_path() -> str:
    return get_project_path() or ""


def _map_error_code(tool_name: str, message: str) -> str:
    lower = (message or "").lower()
    if "enoent" in lower or "not found" in lower:
        return "NOT_FOUND"
    if "denied" in lower or "拒绝" in lower:
        return "PATH_DENIED"
    if tool_name == "write_file":
        return "WRITE_FAILED"
    return f"{tool_name.upper()}_FAILED"


@tool
def read_file(path: str) -> str:
    """读取项目文件，返回统一 JSON。"""
    full_path = normalize_path(path, _current_project_path())
    try:
        content = call_mcp_tool("read_file", {"path": full_path})
        if isinstance(content, str) and content.lstrip().startswith("ENOENT:"):
            return _error("NOT_FOUND", content.strip(), {"path": path})
        return _success(
            f"已读取 {path}",
            {"path": path, "content": _truncate(content)},
        )
    except Exception as exc:
        return _error(_map_error_code("read_file", str(exc)), str(exc), {"path": path})


@tool
def write_file(path: str, content: str) -> str:
    """写入项目文件，返回统一 JSON。"""
    try:
        result = safe_write_file(path, content, _current_project_path())
    except Exception as exc:
        return _error(_map_error_code("write_file", str(exc)), str(exc), {"path": path})

    if not result.get("success"):
        return _error(
            _map_error_code("write_file", result.get("error", "")),
            result.get("error", "写入失败"),
            {"path": path},
        )

    return _success(
        f"已写入 {path}",
        {
            "path": path,
            "is_new": bool(result.get("is_new")),
            "diff": _truncate(result.get("diff", ""), limit=4000),
        },
    )


@tool
def list_directory(path: str) -> str:
    """列出目录内容，返回统一 JSON。"""
    full_path = normalize_path(path, _current_project_path())
    try:
        result = call_mcp_tool("list_directory", {"path": full_path})
        return _success(
            f"已列出 {path}",
            {"path": path, "listing": _truncate(result)},
        )
    except Exception as exc:
        return _error(_map_error_code("list_directory", str(exc)), str(exc), {"path": path})


@tool
def search_files(path: str, pattern: str) -> str:
    """搜索文件内容，返回统一 JSON。"""
    full_path = normalize_path(path, _current_project_path())
    try:
        result = call_mcp_tool("search_files", {"path": full_path, "pattern": pattern})
        return _success(
            f"已搜索 {path} 中的 {pattern}",
            {"path": path, "pattern": pattern, "matches": _truncate(result)},
        )
    except Exception as exc:
        return _error(
            _map_error_code("search_files", str(exc)),
            str(exc),
            {"path": path, "pattern": pattern},
        )


TOOL_REGISTRY: dict[str, BaseTool] = {
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "search_files": search_files,
}


def build_langchain_tools(spec: WorkerSpec) -> list[BaseTool]:
    allowed = {
        item["function"]["name"]
        for item in build_tool_definitions(spec.tool_profile)
        if item["function"]["name"] in spec.tools
    }
    return [TOOL_REGISTRY[name] for name in spec.tools if name in allowed and name in TOOL_REGISTRY]


def build_worker_agent(spec: WorkerSpec):
    """把 WorkerSpec 变成官方 LangGraph ReAct Agent。"""
    tools = build_langchain_tools(spec)
    if not spec.enabled and tools:
        logger.warning(f"Stub worker {spec.name} 不应暴露工具，已忽略配置工具: {spec.tools}")
        tools = []

    llm = create_llm(task_type=spec.task_type, temperature=0.2)
    return create_react_agent(
        model=llm,
        tools=tools,
        name=spec.name,
        prompt=spec.system_prompt,
    )
