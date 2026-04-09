import json
import time

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from agents.llm import create_llm
from config.logger import logger
from config.settings import Settings
from context.loader import build_system_prompt
from database.db import db
from graphs.safety import execute_tool_safely
from mcp_tools.mcp_client import get_all_mcp_tools, get_project_path


READ_ONLY_TOOLS = {
    "read_file",
    "list_directory",
    "search_files",
    "scan_asset_sizes",
    "scan_texture_info",
    "read_project_settings",
    "parse_meta_file",
    "find_references",
}

WRITE_ENABLED_SKILLS = {
    "generate_test",
    "generate_system",
    "generate_shader",
    "generate_ui",
    "generate_editor_tool",
    "translate",
}


def _extract_total_tokens(response) -> int:
    usage = response.response_metadata.get("token_usage", {}) if getattr(response, "response_metadata", None) else {}
    if "total_tokens" in usage:
        return usage["total_tokens"] or 0
    usage2 = getattr(response, "usage_metadata", None) or {}
    return usage2.get("total_tokens", 0) or 0


def _content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
        return "\n".join(parts)
    return str(content or "")


def _build_tool_definitions(skill_id: str) -> list[dict]:
    tool_defs = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "读取项目文件内容",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "文件路径"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "写入文件（自动备份和验证）",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": "列出目录内容",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "目录路径"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_files",
                "description": "搜索包含关键字的文件",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "pattern": {"type": "string"}},
                    "required": ["path", "pattern"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "scan_asset_sizes",
                "description": "统计资源文件大小",
                "parameters": {
                    "type": "object",
                    "properties": {"relative_path": {"type": "string", "default": "Assets"}},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "scan_texture_info",
                "description": "扫描纹理文件信息",
                "parameters": {
                    "type": "object",
                    "properties": {"relative_path": {"type": "string", "default": "Assets"}},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_project_settings",
                "description": "读取 ProjectSettings 配置文件",
                "parameters": {
                    "type": "object",
                    "properties": {"settings_file": {"type": "string"}},
                    "required": ["settings_file"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "parse_meta_file",
                "description": "解析 .meta 获取 GUID",
                "parameters": {
                    "type": "object",
                    "properties": {"relative_path": {"type": "string"}},
                    "required": ["relative_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "find_references",
                "description": "搜索 GUID 引用",
                "parameters": {
                    "type": "object",
                    "properties": {"guid": {"type": "string"}},
                    "required": ["guid"],
                },
            },
        },
    ]

    registered = set(get_all_mcp_tools())
    allowed_tools = set(READ_ONLY_TOOLS)
    if skill_id in WRITE_ENABLED_SKILLS:
        allowed_tools.add("write_file")

    return [
        tool
        for tool in tool_defs
        if tool["function"]["name"] in registered and tool["function"]["name"] in allowed_tools
    ]


def run_agent_loop(
    user_input: str,
    skill: dict = None,
    schema: dict = None,
    project_context: dict = None,
    chat_history: list = None,
) -> dict:
    """核心 Agent Loop"""
    t0 = time.time()
    skill_id = skill["skill_id"] if skill else "unknown"
    task_id = db.log_task_start(skill_id, user_input[:200])
    project_path = get_project_path() or (project_context or {}).get("project_path", "")

    system = build_system_prompt(skill, schema, project_context)
    messages = [SystemMessage(content=system)]

    if chat_history:
        for msg in chat_history[-6:]:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

    plan_prompt = (
        f"用户需求：{user_input}\n\n"
        "请先输出你的执行计划（编号列表），然后逐步执行。\n"
        "每完成一步，简要报告结果并继续下一步。\n"
        "如果某步失败，说明原因并调整计划。"
    )
    messages.append(HumanMessage(content=plan_prompt))

    tool_defs = _build_tool_definitions(skill_id)
    task_type = "review" if skill_id in ("review_code", "analyze_perf") else "generation"
    llm = create_llm(task_type=task_type)
    if tool_defs:
        llm = llm.bind_tools(tool_defs)

    total_tokens = 0
    output_files = []

    for step in range(Settings.MAX_AGENT_STEPS):
        try:
            response = llm.invoke(messages)
        except Exception as exc:
            logger.error(f"LLM 调用失败 (step {step}): {exc}")
            time.sleep(2)
            try:
                response = llm.invoke(messages)
            except Exception as exc2:
                duration = time.time() - t0
                db.log_task_end(task_id, "failed", total_tokens, duration, str(exc2))
                return {
                    "status": "failed",
                    "error": f"LLM 调用失败: {exc2}",
                    "tokens": total_tokens,
                    "display": f"❌ LLM 调用失败: {exc2}",
                    "duration": duration,
                }

        messages.append(response)
        total_tokens += _extract_total_tokens(response)

        if not response.tool_calls:
            break

        for call in response.tool_calls:
            tool_name = call["name"]
            tool_args = call["args"]
            logger.debug(f"Tool call [{step}]: {tool_name}({json.dumps(tool_args, ensure_ascii=False)[:100]})")

            result = execute_tool_safely(tool_name, tool_args, project_path)
            if tool_name == "write_file" and "成功写入" in result:
                output_files.append(tool_args.get("path", ""))

            messages.append(ToolMessage(content=result, tool_call_id=call["id"]))

    final_content = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            final_content = _content_to_text(msg.content)
            break

    if not final_content:
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_content = _content_to_text(msg.content)
                break

    duration = time.time() - t0
    status = "success" if final_content else "failed"

    display = final_content
    if output_files:
        display += "\n\n### 生成的文件\n"
        for file_path in output_files:
            display += f"- ✅ {file_path}\n"

    db.log_task_end(task_id, status, total_tokens, duration)

    return {
        "status": status,
        "display": display,
        "tokens": total_tokens,
        "duration": duration,
        "output_files": output_files,
        "steps": len([msg for msg in messages if isinstance(msg, ToolMessage)]),
    }
