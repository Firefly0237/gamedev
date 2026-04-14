import json
import time

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from agents.llm import create_llm
from config.logger import logger
from config.settings import Settings
from context.loader import build_system_prompt, extract_focus_class
from database.db import db
from graphs.safety import execute_tool_safely
from mcp_tools.mcp_client import ENGINE_TOOL_MAP, get_all_mcp_tools, get_project_path
from schemas.contracts import empty_result


READ_ONLY_TOOLS = {
    "read_file",
    "list_directory",
    "search_files",
    "scan_asset_sizes",
    "scan_texture_info",
    "read_project_settings",
    "parse_meta_file",
    "find_references",
    "validate_all_configs",
    "engine_compile",
    "engine_run_tests",
    "engine_get_logs",
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
        {
            "type": "function",
            "function": {
                "name": "validate_all_configs",
                "description": "校验项目所有配置文件，返回问题列表",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "engine_compile",
                "description": "调用引擎编译当前项目，返回错误和警告列表。需要 Unity Server 连接。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "engine_run_tests",
                "description": "运行项目的单元测试，返回 passed/failed 统计和失败详情",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "test_filter": {"type": "string", "description": "可选的测试名过滤器"}
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "engine_get_logs",
                "description": "读取最近的引擎日志（用于查看编译/运行历史输出）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lines": {"type": "integer", "default": 100}
                    },
                },
            },
        },
    ]

    registered = set(get_all_mcp_tools())
    allowed_tools = set(READ_ONLY_TOOLS)
    if skill_id in WRITE_ENABLED_SKILLS:
        allowed_tools.add("write_file")

    engine_map = ENGINE_TOOL_MAP.get("unity", {})
    available = []
    for tool in tool_defs:
        name = tool["function"]["name"]
        if name not in allowed_tools:
            continue
        if name in registered:
            available.append(tool)
            continue
        if name in engine_map and engine_map[name] in registered:
            available.append(tool)
    return available


def run_agent_loop(
    user_input: str,
    skill: dict = None,
    schema: dict = None,
    project_context: dict = None,
    chat_history: list = None,
    tool_filter: list[str] = None,
    max_steps: int = None,
    extra_user_prompt: str = None,
    temperature: float = None,
) -> dict:
    """核心 Agent Loop"""
    t0 = time.time()
    skill_id = skill["skill_id"] if skill else "unknown"
    task_id = db.log_task_start(skill_id, user_input[:200])
    project_path = get_project_path() or (project_context or {}).get("project_path", "")

    focus = extract_focus_class(user_input, project_context or {})
    system = build_system_prompt(skill, schema, project_context, focus_class=focus)
    messages = [SystemMessage(content=system)]

    if chat_history:
        for msg in chat_history[-6:]:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

    full_input = user_input
    if extra_user_prompt:
        full_input = f"{user_input}\n\n{extra_user_prompt}"

    plan_prompt = (
        f"用户需求：{full_input}\n\n"
        "请先输出你的执行计划（编号列表），然后逐步执行。\n"
        "每完成一步，简要报告结果并继续下一步。\n"
        "如果某步失败，说明原因并调整计划。"
    )
    messages.append(HumanMessage(content=plan_prompt))

    tool_defs = _build_tool_definitions(skill_id)
    if tool_filter is not None:
        tool_defs = [tool for tool in tool_defs if tool["function"]["name"] in tool_filter]
        logger.info(f"工具过滤: {len(tool_defs)} 个工具可用 ({tool_filter})")

    tool_names = {tool["function"]["name"] for tool in tool_defs}
    if skill_id == "validate_build" and not (
        {"engine_compile", "engine_run_tests", "engine_get_logs"} & tool_names
    ):
        duration = time.time() - t0
        db.log_task_end(task_id, "failed", 0, duration, "Unity 未配置或 Unity Server 未连接")
        result = empty_result(route="agent_loop", task_id=task_id)
        result["status"] = "failed"
        result["summary"] = "Unity 编译/测试不可用"
        result["display"] = (
            "❌ Unity 未配置或 Unity Server 未连接，当前无法执行真实编译/测试。\n\n"
            "请在 .env 中设置 UNITY_EXECUTABLE_PATH，并重启 GameDev。"
        )
        result["error"] = "Unity 未配置或 Unity Server 未连接"
        result["duration"] = duration
        return result

    task_type = "review" if skill_id in ("review_code", "analyze_perf") else "generation"
    effective_temp = temperature if temperature is not None else None
    llm = create_llm(task_type=task_type, temperature=effective_temp)
    if tool_defs:
        llm = llm.bind_tools(tool_defs)

    total_tokens = 0
    output_files = []

    effective_max_steps = max_steps if max_steps is not None else Settings.MAX_AGENT_STEPS
    for step in range(effective_max_steps):
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
                result = empty_result(route="agent_loop", task_id=task_id)
                result["status"] = "failed"
                result["error"] = f"LLM 调用失败: {exc2}"
                result["display"] = f"❌ LLM 调用失败: {exc2}"
                result["tokens"] = total_tokens
                result["duration"] = duration
                return result

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
    output_files = list(dict.fromkeys(output_files))
    if output_files:
        display += "\n\n### 生成的文件\n"
        for file_path in output_files:
            display += f"- ✅ {file_path}\n"

    summary = ""
    if final_content:
        first_line = final_content.split("\n")[0].strip()
        summary = first_line[:80] if first_line else final_content[:80]

    steps_count = len([msg for msg in messages if isinstance(msg, ToolMessage)])

    db.log_task_end(task_id, status, total_tokens, duration)

    result = empty_result(route="agent_loop", task_id=task_id)
    result["status"] = status
    result["display"] = display
    result["summary"] = summary or f"{skill_id} 完成"
    result["output_files"] = output_files
    result["steps"] = steps_count
    result["tokens"] = total_tokens
    result["duration"] = duration
    if status == "failed":
        result["error"] = "未生成最终输出"
        if not result["display"]:
            result["display"] = "❌ 未生成最终输出"
    return result
