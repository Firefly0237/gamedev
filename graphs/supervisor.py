import os
import re
import time

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from agents.llm import create_llm
from config.logger import logger
from config.settings import Settings
from context.loader import build_system_prompt
from database.db import db
from graphs.agent_loop import _build_tool_definitions, run_agent_loop
from graphs.safety import execute_tool_safely, normalize_path
from graphs.verify import verify_files
from mcp_tools.mcp_client import get_project_path
from schemas.contracts import empty_result
from schemas.outputs import SubTaskPlan, try_parse


TOOL_FILTERS = {
    "read": ["read_file", "list_directory", "search_files"],
    "write": ["read_file", "write_file", "list_directory"],
    "verify": ["read_file", "engine_compile", "engine_run_tests", "validate_all_configs"],
    "mixed": ["read_file", "write_file", "list_directory", "search_files"],
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


def _build_plan_system_prompt(skill: dict, project_context: dict) -> str:
    """PLAN 阶段的 System Prompt：让模型输出 SubTaskPlan JSON"""
    base = build_system_prompt(skill, None, project_context)

    plan_instruction = """

## Supervisor 规划要求

你现在处于 Supervisor 的 PLAN 阶段。任务是把用户需求拆解为可执行的子任务清单。

输出格式必须严格遵守 SubTaskPlan JSON：

```json
{
  "subtasks": [
    {
      "step_id": 1,
      "description": "创建 XxxData.cs 数据类，包含字段...",
      "target_files": ["Assets/Scripts/Data/XxxData.cs"],
      "tool_hint": "write",
      "depends_on": []
    },
    {
      "step_id": 2,
      "description": "创建 XxxConfig.json 配置数据",
      "target_files": ["Assets/Resources/Configs/XxxConfig.json"],
      "tool_hint": "write",
      "depends_on": [1]
    }
  ],
  "summary": "完成 Xxx 系统的数据层和配置层"
}
```

规则：
1. 子任务数量不超过 8 个。如果任务太复杂，先输出最核心的部分
2. 每个 description 必须具体到字段名/方法名，不能写"实现 XX 功能"这种泛泛描述
3. 每个 description 控制在 120 个中文字符以内，绝不能超过 200 个字符
4. target_files 必须用相对项目根的路径（Assets/... 开头）
5. tool_hint 必须是 read / write / verify / mixed 之一
6. depends_on 列出依赖的前置 step_id（如生成测试要依赖被测的源文件已生成）
7. 按依赖顺序排列，无依赖的放前面
8. 数据类 → 配置 → 逻辑 → 测试 是常见的依赖顺序

只输出 JSON，不要任何额外说明文字。
"""
    return base + plan_instruction


def _extract_json_payload(text: str):
    json_str = text
    match = re.search(r"```json\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        match = re.search(r"```\s*\n(.*?)\n\s*```", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                json_str = match.group(0)
    return json.loads(json_str)


def _try_parse_plan(text: str) -> tuple[SubTaskPlan | None, str]:
    result, err = try_parse(text, SubTaskPlan)
    if result:
        return result, ""

    try:
        parsed = _extract_json_payload(text)
        subtasks = parsed.get("subtasks", [])
        if isinstance(subtasks, list):
            normalized = []
            for subtask in subtasks:
                if isinstance(subtask, dict):
                    item = dict(subtask)
                    description = item.get("description")
                    if isinstance(description, str) and len(description) > 200:
                        item["description"] = description[:200].rstrip()
                    normalized.append(item)
                else:
                    normalized.append(subtask)
            parsed["subtasks"] = normalized
            coerced = SubTaskPlan(**parsed)
            logger.info("PLAN 输出已自动压缩 description 长度后通过校验")
            return coerced, ""
    except Exception:
        pass

    return None, err


def run_plan(user_input: str, skill: dict, project_context: dict) -> tuple:
    """PLAN 阶段：生成 SubTaskPlan
    Returns:
        (plan: SubTaskPlan | None, tokens: int, error: str)
    """
    system = _build_plan_system_prompt(skill, project_context)
    llm_base = create_llm(task_type="generation", temperature=0.1)
    plan_tools = [
        tool
        for tool in _build_tool_definitions(skill["skill_id"] if skill else "generate_system")
        if tool["function"]["name"] in TOOL_FILTERS["read"]
    ]

    total_tokens = 0
    plan = None
    last_error = ""
    project_path = get_project_path() or (project_context or {}).get("project_path", "")

    for attempt in range(Settings.MAX_RETRIES):
        use_tools = attempt > 0 and bool(plan_tools)
        llm = llm_base.bind_tools(plan_tools) if use_tools else llm_base
        messages = [SystemMessage(content=system)]
        prompt = user_input
        if attempt == 0:
            prompt = (
                f"{user_input}\n\n"
                "请优先基于已给的项目上下文直接输出严格的 SubTaskPlan JSON。"
                "这一轮不要调用任何工具。"
            )
        else:
            prompt = (
                f"{user_input}\n\n上次输出格式错误: {last_error}\n"
                "请严格输出 SubTaskPlan JSON。只有在确实缺少信息时才调用只读工具。"
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
            total_tokens += _extract_total_tokens(resp)

            if not resp.tool_calls:
                final_text = _content_to_text(resp.content)
                break

            for call in resp.tool_calls:
                result = execute_tool_safely(call["name"], call["args"], project_path)
                messages.append(ToolMessage(content=result, tool_call_id=call["id"]))

        if not final_text:
            if not last_error:
                last_error = f"PLAN 未在 {max_plan_steps} 步内输出 SubTaskPlan JSON"
            logger.warning(f"PLAN 第{attempt + 1}次未收敛: {last_error}")
            continue

        result, err = _try_parse_plan(final_text)
        if result:
            plan = result
            logger.info(f"PLAN 成功: {len(plan.subtasks)} 个 subtask")
            break
        last_error = err
        logger.warning(f"PLAN 第{attempt + 1}次解析失败: {err[:100]}")

    return plan, total_tokens, last_error


def run_execute(plan, project_context: dict, skill: dict | None = None) -> dict:
    """EXECUTE 阶段：依次执行每个 subtask"""
    completed = []
    created_files = []
    total_tokens = 0
    all_results = []
    project_path = get_project_path() or (project_context or {}).get("project_path", "")

    for subtask in plan.subtasks:
        deps_satisfied = all(dep in completed for dep in subtask.depends_on)
        if not deps_satisfied:
            logger.warning(f"Subtask {subtask.step_id} 依赖未满足: {subtask.depends_on}")
            return {
                "status": "failed",
                "completed_subtasks": completed,
                "failed_subtask": subtask,
                "failed_error": f"前置依赖未完成: {subtask.depends_on}",
                "created_files": created_files,
                "tokens": total_tokens,
                "all_results": all_results,
            }

        tool_filter = TOOL_FILTERS.get(subtask.tool_hint, TOOL_FILTERS["mixed"])
        subtask_input = (
            f"{subtask.description}\n\n"
            f"目标文件: {', '.join(subtask.target_files)}\n"
            "完成后简要确认结果。"
        )
        extra_prompt = None
        if subtask.tool_hint in ("write", "mixed"):
            extra_prompt = (
                "当前处于 Supervisor 的 EXECUTE 阶段。"
                "你必须直接完成该子任务，并实际调用 write_file 写入所有目标文件。"
                "不要只解释方案，不要只输出代码片段，不要修改目标文件之外的文件。"
            )

        logger.info(f"EXECUTE subtask {subtask.step_id}/{len(plan.subtasks)}: {subtask.description[:60]}")

        result = run_agent_loop(
            user_input=subtask_input,
            skill=skill,
            project_context=project_context,
            chat_history=None,
            tool_filter=tool_filter,
            max_steps=5,
            extra_user_prompt=extra_prompt,
            temperature=0.2,
        )

        all_results.append(result)
        total_tokens += result.get("tokens", 0)

        if result["status"] == "success":
            generated_files = list(result.get("output_files", []))
            if subtask.tool_hint in ("write", "mixed") and not generated_files:
                for target_file in subtask.target_files:
                    full_path = normalize_path(target_file, project_path)
                    if full_path and os.path.exists(full_path):
                        generated_files.append(target_file)

            if subtask.tool_hint in ("write", "mixed") and not generated_files:
                logger.warning(f"  ❌ subtask {subtask.step_id} 未生成目标文件")
                return {
                    "status": "failed",
                    "completed_subtasks": completed,
                    "failed_subtask": subtask,
                    "failed_error": "执行成功但未生成任何目标文件",
                    "created_files": created_files,
                    "tokens": total_tokens,
                    "all_results": all_results,
                }

            result["output_files"] = generated_files
            completed.append(subtask.step_id)
            for file_path in generated_files:
                if file_path not in created_files:
                    created_files.append(file_path)
            logger.info(f"  ✅ subtask {subtask.step_id} 完成")
        else:
            logger.warning(f"  ❌ subtask {subtask.step_id} 失败: {result.get('error', '')[:100]}")
            return {
                "status": "failed",
                "completed_subtasks": completed,
                "failed_subtask": subtask,
                "failed_error": result.get("error", result.get("display", "未知错误"))[:500],
                "created_files": created_files,
                "tokens": total_tokens,
                "all_results": all_results,
            }

    return {
        "status": "success",
        "completed_subtasks": completed,
        "failed_subtask": None,
        "failed_error": "",
        "created_files": created_files,
        "tokens": total_tokens,
        "all_results": all_results,
    }


def run_verify(created_files: list[str], project_context: dict) -> dict:
    """VERIFY 阶段：调用通用验证器。"""
    return verify_files(
        files=created_files,
        project_context=project_context,
        mode="full",
        skill_id="generate_system",
    )


def run_fix_loop(
    plan,
    execute_result: dict,
    verify_result: dict,
    project_context: dict,
    skill: dict | None = None,
) -> tuple:
    """FIX_LOOP：定位失败文件 → 重新执行对应 subtask"""
    failed_files = set()
    for detail in verify_result["details"]:
        if not detail["passed"] and detail["type"] == "syntax":
            msg = detail["message"]
            if ":" in msg:
                failed_files.add(msg.split(":", 1)[0].strip())
        elif not detail["passed"] and detail["type"] == "compile":
            for file_path in execute_result["created_files"]:
                if file_path.endswith(".cs"):
                    failed_files.add(file_path)

    if not failed_files:
        logger.warning("FIX_LOOP: 无法定位失败文件")
        return execute_result, verify_result, 0

    subtasks_to_retry = []
    for subtask in plan.subtasks:
        if any(target in failed_files for target in subtask.target_files):
            subtasks_to_retry.append(subtask)

    if not subtasks_to_retry:
        logger.warning("FIX_LOOP: 失败文件不在任何 subtask 中")
        return execute_result, verify_result, 0

    logger.info(f"FIX_LOOP: 重试 {len(subtasks_to_retry)} 个 subtask")

    error_summary = "\n".join(f"- {detail['message']}" for detail in verify_result["details"] if not detail["passed"])
    fix_prompt = f"上次生成的代码验证失败，错误如下:\n{error_summary}\n\n请重新生成正确的代码，注意修复上述错误。"

    total_tokens = 0
    new_created = list(execute_result["created_files"])

    for subtask in subtasks_to_retry:
        tool_filter = TOOL_FILTERS.get(subtask.tool_hint, TOOL_FILTERS["mixed"])
        subtask_input = f"{subtask.description}\n\n目标文件: {', '.join(subtask.target_files)}"
        extra_prompt = fix_prompt
        if subtask.tool_hint in ("write", "mixed"):
            extra_prompt += (
                "\n\n你必须实际调用 write_file 重写目标文件，"
                "不要只描述修复思路。"
            )

        result = run_agent_loop(
            user_input=subtask_input,
            skill=skill,
            project_context=project_context,
            tool_filter=tool_filter,
            max_steps=5,
            temperature=0.1,
            extra_user_prompt=extra_prompt,
        )

        total_tokens += result.get("tokens", 0)
        if result["status"] != "success":
            logger.warning(f"FIX_LOOP: subtask {subtask.step_id} 修复失败")
            return execute_result, verify_result, total_tokens

        for file_path in result.get("output_files", []):
            if file_path not in new_created:
                new_created.append(file_path)

    fixed_execute = dict(execute_result)
    fixed_execute["created_files"] = new_created
    fixed_execute["all_results"] = execute_result.get("all_results", [])
    fixed_verify = run_verify(new_created, project_context)
    return fixed_execute, fixed_verify, total_tokens


def run_supervisor(
    user_input: str,
    skill: dict,
    schema: dict,
    project_context: dict,
    chat_history: list = None,
) -> dict:
    """Supervisor 主入口：PLAN → EXECUTE → VERIFY → (FIX_LOOP)"""
    t0 = time.time()
    skill_id = skill["skill_id"] if skill else "supervisor"
    task_id = db.log_task_start(skill_id, user_input[:200])

    total_tokens = 0
    result = empty_result(route="supervisor", task_id=task_id)

    logger.info(f"=== Supervisor 启动: {user_input[:50]} ===")
    plan, plan_tokens, plan_error = run_plan(user_input, skill, project_context)
    total_tokens += plan_tokens

    if not plan:
        result["status"] = "failed"
        result["error"] = f"PLAN 失败: {plan_error}"
        result["display"] = f"❌ 任务规划失败\n\n{plan_error}"
        result["tokens"] = total_tokens
        result["duration"] = time.time() - t0
        db.log_task_end(task_id, "failed", total_tokens, result["duration"], plan_error)
        return result

    execute_result = run_execute(plan, project_context, skill)
    total_tokens += execute_result["tokens"]

    if execute_result["status"] == "failed":
        result["status"] = "partial" if execute_result["completed_subtasks"] else "failed"
        result["output_files"] = execute_result["created_files"]
        result["actions"] = [{"step_id": sid, "completed": True} for sid in execute_result["completed_subtasks"]]
        failed_subtask = execute_result["failed_subtask"]
        result["error"] = (
            f"Subtask {failed_subtask.step_id} 失败: {execute_result['failed_error']}"
            if failed_subtask
            else execute_result["failed_error"]
        )
        result["display"] = _format_partial_display(plan, execute_result, None)
        result["summary"] = f"{plan.summary}（部分完成）"
        result["tokens"] = total_tokens
        result["duration"] = time.time() - t0
        db.log_task_end(task_id, result["status"], total_tokens, result["duration"], result["error"])
        return result

    verify_result = run_verify(execute_result["created_files"], project_context)
    if not verify_result["passed"]:
        logger.info("VERIFY 失败，进入 FIX_LOOP")
        execute_result, verify_result, fix_tokens = run_fix_loop(
            plan,
            execute_result,
            verify_result,
            project_context,
            skill,
        )
        total_tokens += fix_tokens

    status = "success" if verify_result["passed"] else "partial"
    result["status"] = status
    result["output_files"] = execute_result["created_files"]
    result["actions"] = [
        {"step_id": subtask.step_id, "description": subtask.description, "files": subtask.target_files}
        for subtask in plan.subtasks
    ]
    result["verification"] = verify_result
    result["summary"] = plan.summary
    result["display"] = _format_full_display(plan, execute_result, verify_result)
    result["tokens"] = total_tokens
    result["duration"] = time.time() - t0
    result["steps"] = sum(item.get("steps", 0) for item in execute_result["all_results"])

    db.log_task_end(task_id, status, total_tokens, result["duration"])
    return result


def _format_partial_display(plan, execute_result, verify_result):
    """部分完成时的展示文本"""
    lines = [f"## ⚠️ 部分完成: {plan.summary}\n"]

    completed = set(execute_result["completed_subtasks"])
    for subtask in plan.subtasks:
        if subtask.step_id in completed:
            lines.append(f"- ✅ Step {subtask.step_id}: {subtask.description[:80]}")
        elif subtask == execute_result["failed_subtask"]:
            lines.append(f"- ❌ Step {subtask.step_id}: {subtask.description[:80]}")
            lines.append(f"  错误: {execute_result['failed_error'][:200]}")
        else:
            lines.append(f"- ⏸️ Step {subtask.step_id}: {subtask.description[:80]} (未执行)")

    if execute_result["created_files"]:
        lines.append(f"\n### 已生成 {len(execute_result['created_files'])} 个文件")
        for file_path in execute_result["created_files"]:
            lines.append(f"- {file_path}")

    return "\n".join(lines)


def _format_full_display(plan, execute_result, verify_result):
    """完整执行的展示文本"""
    lines = [f"## {'✅' if verify_result['passed'] else '⚠️'} {plan.summary}\n"]

    lines.append(f"### 执行步骤 ({len(plan.subtasks)} 个)\n")
    for subtask in plan.subtasks:
        lines.append(f"- ✅ Step {subtask.step_id}: {subtask.description[:80]}")

    lines.append(f"\n### 生成文件 ({len(execute_result['created_files'])} 个)\n")
    for file_path in execute_result["created_files"]:
        lines.append(f"- {file_path}")

    lines.append("\n### 验证结果\n")
    for detail in verify_result["details"]:
        emoji = "✅" if detail["passed"] else "❌"
        lines.append(f"- {emoji} [{detail['type']}] {detail['message']}")

    return "\n".join(lines)
