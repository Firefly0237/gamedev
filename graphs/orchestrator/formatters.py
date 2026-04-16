from __future__ import annotations

from schemas.contracts import empty_result
from schemas.outputs import SubTaskPlan


def failed_result(message: str, tokens: int = 0, status: str = "failed") -> dict:
    result = empty_result(route="orchestrator")
    result["status"] = status
    result["summary"] = "任务未执行" if status == "failed" else "任务已取消"
    result["display"] = f"❌ {message}" if status == "failed" else f"ℹ️ {message}"
    result["error"] = message
    result["tokens"] = tokens
    return result


def plan_actions(plan: SubTaskPlan, step_results: dict[int, dict] | None = None) -> list[dict]:
    step_results = step_results or {}
    actions = []
    for subtask in plan.subtasks:
        step_result = step_results.get(subtask.step_id, {})
        actions.append(
            {
                "step_id": subtask.step_id,
                "description": subtask.description,
                "files": subtask.target_files,
                "tool_hint": subtask.tool_hint,
                "depends_on": subtask.depends_on,
                "worker": step_result.get("worker", ""),
                "status": step_result.get("status", "pending"),
                "summary": step_result.get("summary", ""),
                "error_code": step_result.get("error_code", ""),
            }
        )
    return actions


def format_plan_preview(plan: SubTaskPlan) -> str:
    lines = [f"## 📋 {plan.summary}", "", "等待确认的执行计划："]
    for subtask in plan.subtasks:
        lines.append(f"- Step {subtask.step_id}: {subtask.description}")
        lines.append(f"  文件: {', '.join(subtask.target_files)}")
    return "\n".join(lines)


def build_subtask_message(plan: SubTaskPlan, subtask, route_agent_hint: str = "") -> str:
    lines = [
        f"任务摘要：{plan.summary}",
        f"当前子任务：Step {subtask.step_id}/{len(plan.subtasks)}",
        f"描述：{subtask.description}",
        f"目标文件：{', '.join(subtask.target_files)}",
        f"工具倾向：{subtask.tool_hint}",
    ]
    if subtask.depends_on:
        lines.append(f"已满足依赖：{', '.join(str(dep) for dep in subtask.depends_on)}")
    if route_agent_hint:
        lines.append(f"默认建议 Worker：{route_agent_hint}")

    lines.extend(
        [
            "",
            "执行要求：",
            "1. 只完成这个子任务，不要处理其他 step。",
            "2. 如果该任务不属于你的职责范围，返回 failed 并使用 error_code=DOMAIN_MISMATCH。",
            "3. 如果是写文件任务，必须真实调用 write_file，且 created_files 只列出实际成功写入的路径。",
            "4. 最终只输出 Worker JSON 结果，不要附加额外说明。",
        ]
    )
    return "\n".join(lines)


def format_result(plan: SubTaskPlan, step_results: dict[int, dict], verify_result: dict) -> str:
    status_icon = "✅" if verify_result.get("passed") else "⚠️"
    lines = [f"## {status_icon} {plan.summary}", "", "### 子任务结果"]
    for subtask in plan.subtasks:
        result = step_results.get(subtask.step_id, {})
        if result.get("status") == "success":
            worker = result.get("worker", "worker")
            lines.append(f"- ✅ Step {subtask.step_id} [{worker}]: {result.get('summary', subtask.description)}")
        else:
            worker = result.get("worker", "worker")
            code = result.get("error_code", "UNKNOWN")
            details = result.get("error_details", result.get("summary", ""))
            lines.append(f"- ❌ Step {subtask.step_id} [{worker}]: {code} - {details}")

    created_files = []
    for result in step_results.values():
        for file_path in result.get("created_files", []):
            if file_path not in created_files:
                created_files.append(file_path)
    if created_files:
        lines.extend(["", "### 输出文件"])
        for file_path in created_files:
            lines.append(f"- {file_path}")

    if verify_result.get("details"):
        lines.extend(["", "### 验证结果"])
        for detail in verify_result["details"]:
            emoji = "✅" if detail.get("passed") else "❌"
            lines.append(f"- {emoji} [{detail.get('type', 'check')}] {detail.get('message', '')}")

    return "\n".join(lines)
