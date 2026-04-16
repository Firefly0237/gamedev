from __future__ import annotations

import time
import uuid

from database.db import db
from schemas.contracts import empty_result
from schemas.outputs import SubTaskPlan

from .executor import execute_plan
from .formatters import failed_result, format_plan_preview, format_result, plan_actions
from .planner import run_planner
from .runtime import get_graph
from .verifier import run_verifier


def _planner_model_usage(plan_llm_info, tokens: int) -> list[dict]:
    return [
        {
            "role": "planner",
            "task_type": "plan",
            "provider": plan_llm_info.provider if plan_llm_info else "",
            "model": plan_llm_info.model if plan_llm_info else "",
            "tokens": tokens,
        }
    ]


def _worker_model_usage(step_results: dict[int, dict]) -> list[dict]:
    usage = []
    for step_id, step_result in step_results.items():
        usage.append(
            {
                "role": f"worker:{step_result.get('worker', '') or step_id}",
                "task_type": step_result.get("task_type", ""),
                "provider": step_result.get("provider", ""),
                "model": step_result.get("model", ""),
                "tokens": int(step_result.get("tokens", 0) or 0),
            }
        )
    return usage


def _total_step_tokens(step_results: dict[int, dict]) -> int:
    return sum(int(step_result.get("tokens", 0) or 0) for step_result in step_results.values())


def run_orchestrator(
    user_input: str,
    skill: dict,
    schema: dict,
    project_context: dict,
    chat_history: list | None = None,
) -> dict:
    """阶段 1：生成 Plan，等待用户审批。"""
    del schema, chat_history
    plan, tokens, err, plan_llm_info = run_planner(user_input, skill, project_context)
    if not plan:
        return failed_result(f"PLAN 失败: {err}", tokens)

    return {
        "route": "orchestrator",
        "status": "awaiting_approval",
        "summary": plan.summary,
        "display": format_plan_preview(plan),
        "actions": plan_actions(plan),
        "output_files": [],
        "verification": {"performed": False, "passed": False, "details": []},
        "tokens": tokens,
        "duration": 0.0,
        "error": "",
        "task_id": None,
        "steps": 0,
        "thread_id": str(uuid.uuid4()),
        "plan": plan.model_dump(),
        "plan_model_usage": _planner_model_usage(plan_llm_info, tokens),
        "user_input": user_input,
        "skill": skill,
        "project_context": project_context,
    }


def _cancelled_result(handle: dict) -> dict:
    result = empty_result(route="orchestrator")
    result["status"] = "failed"
    result["summary"] = "任务已取消"
    result["display"] = "ℹ️ 已取消执行计划。"
    result["error"] = "用户取消"
    result["tokens"] = handle.get("tokens", 0)
    return result


def _dependency_failure_result(
    task_id: int,
    plan: SubTaskPlan,
    step_results: dict[int, dict],
    created_files: list[str],
    total_tokens: int,
    duration: float,
    failed_subtask,
    error: str,
) -> dict:
    result = empty_result(route="orchestrator", task_id=task_id)
    result["status"] = "failed" if not step_results else "partial"
    result["summary"] = plan.summary
    result["error"] = error
    result["display"] = f"❌ Step {failed_subtask.step_id} 依赖未满足: {failed_subtask.depends_on}"
    result["actions"] = plan_actions(plan, step_results)
    result["output_files"] = created_files
    result["tokens"] = total_tokens
    result["duration"] = duration
    result["steps"] = len(step_results)
    return result


def _worker_failure_result(
    task_id: int,
    plan: SubTaskPlan,
    step_results: dict[int, dict],
    created_files: list[str],
    total_tokens: int,
    duration: float,
    step_error: dict,
) -> dict:
    result = empty_result(route="orchestrator", task_id=task_id)
    result["status"] = "failed" if len(step_results) == 1 else "partial"
    result["summary"] = plan.summary
    result["error"] = f"{step_error.get('error_code', 'WORKER_FAILED')}: {step_error.get('error_details', '')}"
    result["display"] = format_result(
        plan,
        step_results,
        {"performed": False, "passed": False, "details": []},
    )
    result["actions"] = plan_actions(plan, step_results)
    result["output_files"] = created_files
    result["tokens"] = total_tokens
    result["duration"] = duration
    result["steps"] = len(step_results)
    return result


def resume_orchestrator(handle: dict, approved: bool, stream_callback=None) -> dict:
    """阶段 2：用户批准后按 subtask 调度 worker 图。"""
    if not approved:
        return _cancelled_result(handle)

    plan = SubTaskPlan(**handle["plan"])
    skill = handle.get("skill") or {}
    project_context = handle.get("project_context", {})
    route_agent_hint = skill.get("route_agent_hint", "")
    user_input = handle.get("user_input", "")
    graph = get_graph()

    t0 = time.time()
    task_id = db.log_task_start(skill.get("skill_id", "orchestrator"), user_input[:200])
    plan_model_usage = list(handle.get("plan_model_usage") or [])
    total_tokens = handle.get("tokens", 0)

    step_results, created_files, failure = execute_plan(
        graph,
        plan,
        project_context,
        route_agent_hint=route_agent_hint,
        thread_id=handle["thread_id"],
        stream_callback=stream_callback,
    )

    if failure:
        duration = time.time() - t0
        worker_tokens = _total_step_tokens(step_results)
        total_tokens += worker_tokens
        if "step_result" in failure:
            result = _worker_failure_result(
                task_id,
                plan,
                step_results,
                created_files,
                total_tokens,
                duration,
                failure["step_result"],
            )
        else:
            result = _dependency_failure_result(
                task_id,
                plan,
                step_results,
                created_files,
                total_tokens,
                duration,
                failure["subtask"],
                failure["error"],
            )
        result["model_usage"] = plan_model_usage + _worker_model_usage(step_results)
        db.log_task_end(
            task_id,
            result["status"],
            total_tokens,
            result["duration"],
            result["error"],
            provider=plan_model_usage[0]["provider"] if plan_model_usage else "",
            model=plan_model_usage[0]["model"] if plan_model_usage else "",
        )
        db.save_task_result(task_id, result)
        return result

    verify_result = run_verifier(created_files, project_context, skill.get("skill_id", "generate_system"))
    total_tokens += _total_step_tokens(step_results)

    result = empty_result(route="orchestrator", task_id=task_id)
    result["status"] = "success" if verify_result.get("passed") else "partial"
    result["summary"] = plan.summary
    result["display"] = format_result(plan, step_results, verify_result)
    result["actions"] = plan_actions(plan, step_results)
    result["output_files"] = created_files
    result["verification"] = verify_result
    result["tokens"] = total_tokens
    result["duration"] = time.time() - t0
    result["steps"] = len(step_results)
    result["model_usage"] = plan_model_usage + _worker_model_usage(step_results)
    if result["status"] != "success":
        result["error"] = "验证未完全通过"

    db.log_task_end(
        task_id,
        result["status"],
        total_tokens,
        result["duration"],
        result["error"],
        provider=plan_model_usage[0]["provider"] if plan_model_usage else "",
        model=plan_model_usage[0]["model"] if plan_model_usage else "",
    )
    db.save_task_result(task_id, result)
    return result
