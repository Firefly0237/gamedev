from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from agents.llm import create_llm, get_llm_runtime_info
from config.logger import logger
from config.settings import Settings
from graphs.llm_utils import content_to_text, extract_total_tokens
from graphs.planner_utils import build_plan_system_prompt as _build_plan_system_prompt, try_parse_plan
from graphs.safety import execute_tool_safely
from graphs.tool_defs import build_tool_definitions
from mcp_tools.mcp_client import get_project_path


def run_plan(user_input: str, skill: dict, project_context: dict) -> tuple:
    """Planner 阶段：生成 SubTaskPlan。"""
    system = _build_plan_system_prompt(skill, project_context)
    llm_base = create_llm(task_type="plan", temperature=0.1)
    llm_info = get_llm_runtime_info(llm_base)
    plan_tools = [
        tool
        for tool in build_tool_definitions(skill["skill_id"] if skill else "generate_system")
        if tool["function"]["name"] in ("read_file", "list_directory", "search_files")
    ]

    total_tokens = 0
    plan = None
    last_error = ""
    project_path = get_project_path() or (project_context or {}).get("project_path", "")

    for attempt in range(Settings.MAX_RETRIES):
        use_tools = attempt > 0 and bool(plan_tools)
        llm = llm_base.bind_tools(plan_tools) if use_tools else llm_base
        messages = [SystemMessage(content=system)]
        prompt = (
            f"{user_input}\n\n请直接输出严格的 SubTaskPlan JSON。"
            if attempt == 0
            else (
                f"{user_input}\n\n上次输出格式错误: {last_error}\n"
                "请严格输出 SubTaskPlan JSON。只有在确实缺少信息时才调用只读工具。"
            )
        )
        messages.append(HumanMessage(content=prompt))

        final_text = ""
        max_plan_steps = 4 if use_tools else 1
        for _ in range(max_plan_steps):
            try:
                resp = llm.invoke(messages)
            except Exception as exc:
                last_error = f"LLM 调用失败: {exc}"
                logger.warning(f"PLAN 第{attempt + 1}次 LLM 失败: {exc}")
                final_text = ""
                break

            messages.append(resp)
            total_tokens += extract_total_tokens(resp)

            if not getattr(resp, "tool_calls", None):
                final_text = content_to_text(resp.content)
                break

            for call in resp.tool_calls:
                result = execute_tool_safely(call["name"], call["args"], project_path)
                messages.append(ToolMessage(content=result, tool_call_id=call["id"]))

        if not final_text:
            if not last_error:
                last_error = f"PLAN 未在 {max_plan_steps} 步内输出 SubTaskPlan JSON"
            logger.warning(f"PLAN 第{attempt + 1}次未收敛: {last_error}")
            continue

        result, err = try_parse_plan(final_text)
        if result:
            plan = result
            logger.info(f"PLAN 成功: {len(plan.subtasks)} 个 subtask")
            break
        last_error = err
        logger.warning(f"PLAN 第{attempt + 1}次解析失败: {err[:120]}")

    return plan, total_tokens, last_error, llm_info
