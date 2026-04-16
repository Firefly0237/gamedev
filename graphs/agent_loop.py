import json
import time

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage, ToolMessage

from agents.llm import create_llm, get_llm_runtime_info
from config.logger import logger
from config.settings import Settings
from context.loader import build_system_prompt, extract_focus_class
from database.db import db
from graphs.llm_utils import content_to_text, extract_total_tokens, merge_response_chunks
from graphs.safety import execute_tool_safely
from graphs.tool_defs import build_tool_definitions
from mcp_tools.mcp_client import get_project_path
from schemas.contracts import empty_result

_build_tool_definitions = build_tool_definitions

SKILL_TO_TASK_TYPE = {
    "review_code": "review",
    "analyze_deps": "review",
    "analyze_perf": "review",
    "validate_build": "review",
    "validate_config": "review",
    "translate": "translate",
    "generate_test": "generation",
    "generate_shader": "generation",
    "generate_ui": "generation",
    "generate_editor_tool": "generation",
    "generate_system": "generation",
    "modify_config": "intent_parse",
    "modify_code": "intent_parse",
    "summarize_requirement": "requirement",
}


def resolve_skill_task_type(skill_id: str) -> str:
    return SKILL_TO_TASK_TYPE.get(skill_id, "review")


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
    plan_first: bool = True,
    stream_callback: callable = None,
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

    if plan_first:
        plan_prompt = (
            f"用户需求：{full_input}\n\n"
            "请先输出你的执行计划（编号列表），然后逐步执行。\n"
            "每完成一步，简要报告结果并继续下一步。\n"
            "如果某步失败，说明原因并调整计划。"
        )
        messages.append(HumanMessage(content=plan_prompt))
    else:
        direct_prompt = (
            f"用户需求：{full_input}\n\n"
            "不要先做计划，不要先解释方案，直接开始执行。"
            "如果需要工具，立刻调用；如果完成了，就简要汇报结果。"
        )
        messages.append(HumanMessage(content=direct_prompt))

    tool_defs = _build_tool_definitions(skill_id)
    if tool_filter is not None:
        tool_defs = [tool for tool in tool_defs if tool["function"]["name"] in tool_filter]
        logger.info(f"工具过滤: {len(tool_defs)} 个工具可用 ({tool_filter})")

    tool_names = {tool["function"]["name"] for tool in tool_defs}
    if skill_id == "validate_build" and not (
        {"engine_compile", "engine_run_tests", "engine_get_logs"} & tool_names
    ):
        duration = time.time() - t0
        db.log_task_end(task_id, "failed", 0, duration, "Unity MCP 不可用")
        result = empty_result(route="agent_loop", task_id=task_id)
        result["status"] = "failed"
        result["summary"] = "Unity 编译/测试不可用"
        result["display"] = (
            "❌ Unity MCP 不可用，当前无法执行真实编译/测试。\n\n"
            "请安装 Coplay Unity MCP 包，并确保 Unity Editor 已连接。"
        )
        result["error"] = "Unity MCP 不可用"
        result["duration"] = duration
        return result

    task_type = resolve_skill_task_type(skill_id)
    effective_temp = temperature if temperature is not None else None
    llm = create_llm(task_type=task_type, temperature=effective_temp)
    llm_info = get_llm_runtime_info(llm)
    if tool_defs:
        llm = llm.bind_tools(tool_defs)

    total_tokens = 0
    output_files = []

    effective_max_steps = max_steps if max_steps is not None else Settings.MAX_AGENT_STEPS
    for step in range(effective_max_steps):
        try:
            if stream_callback:
                chunks: list[AIMessageChunk] = []
                for chunk in llm.stream(messages):
                    chunks.append(chunk)
                    text = content_to_text(chunk.content)
                    if text:
                        stream_callback(text)
                response = merge_response_chunks(chunks)
            else:
                response = llm.invoke(messages)
        except Exception as exc:
            logger.error(f"LLM 调用失败 (step {step}): {exc}")
            time.sleep(2)
            try:
                if stream_callback:
                    chunks = []
                    for chunk in llm.stream(messages):
                        chunks.append(chunk)
                        text = content_to_text(chunk.content)
                        if text:
                            stream_callback(text)
                    response = merge_response_chunks(chunks)
                else:
                    response = llm.invoke(messages)
            except Exception as exc2:
                duration = time.time() - t0
                db.log_task_end(
                    task_id,
                    "failed",
                    total_tokens,
                    duration,
                    str(exc2),
                    provider=llm_info.provider if llm_info else "",
                    model=llm_info.model if llm_info else "",
                )
                result = empty_result(route="agent_loop", task_id=task_id)
                result["status"] = "failed"
                result["error"] = f"LLM 调用失败: {exc2}"
                result["display"] = f"❌ LLM 调用失败: {exc2}"
                result["tokens"] = total_tokens
                result["duration"] = duration
                return result

        messages.append(response)
        total_tokens += extract_total_tokens(response)

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
            final_content = content_to_text(msg.content)
            break

    if not final_content:
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_content = content_to_text(msg.content)
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

    result = empty_result(route="agent_loop", task_id=task_id)
    result["status"] = status
    result["display"] = display
    result["summary"] = summary or f"{skill_id} 完成"
    result["output_files"] = output_files
    result["steps"] = steps_count
    result["tokens"] = total_tokens
    result["duration"] = duration
    result["model_usage"] = [
        {
            "role": "agent_loop",
            "task_type": task_type,
            "provider": llm_info.provider if llm_info else "",
            "model": llm_info.model if llm_info else "",
            "tokens": total_tokens,
        }
    ]

    if status == "failed":
        result["error"] = "未生成最终输出"
        if not result["display"]:
            result["display"] = "❌ 未生成最终输出"

    db.log_task_end(
        task_id,
        result["status"],
        result["tokens"],
        result["duration"],
        result["error"],
        provider=llm_info.provider if llm_info else "",
        model=llm_info.model if llm_info else "",
    )
    return result
