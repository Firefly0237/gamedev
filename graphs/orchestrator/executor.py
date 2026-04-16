from __future__ import annotations

import os

from langchain_core.messages import HumanMessage

from agents.llm import resolve_task_model
from config.settings import Settings
from graphs.llm_utils import extract_total_tokens
from graphs.safety import normalize_path
from mcp_tools.mcp_client import get_project_path
from .formatters import build_subtask_message
from .result_parser import latest_worker_payload
from .workers import ALL_SPECS


WORKER_NAMES = {spec.name for spec in ALL_SPECS}
WORKER_SPECS = {spec.name: spec for spec in ALL_SPECS}


def find_missing_targets(target_files: list[str], project_context: dict) -> list[str]:
    project_path = (project_context or {}).get("project_path", "") or get_project_path()
    missing = []
    for rel_path in target_files:
        full_path = normalize_path(rel_path, project_path)
        if not full_path or not os.path.isfile(full_path):
            missing.append(rel_path)
    return missing


def invoke_subtask(
    graph,
    plan,
    subtask,
    thread_id: str,
    project_context: dict,
    route_agent_hint: str,
    stream_callback=None,
) -> dict:
    if stream_callback:
        stream_callback(f"\n### Step {subtask.step_id}: {subtask.description}\n")

    config = {
        "configurable": {"thread_id": f"{thread_id}:{subtask.step_id}"},
        "recursion_limit": max(40, Settings.MAX_HANDOFFS_PER_TASK * 6),
    }
    user_msg = build_subtask_message(plan, subtask, route_agent_hint=route_agent_hint)
    state = graph.invoke({"messages": [HumanMessage(content=user_msg)]}, config=config)
    messages = state.get("messages", []) if isinstance(state, dict) else []
    step_tokens = sum(extract_total_tokens(message) for message in messages)

    payload = latest_worker_payload(messages, WORKER_NAMES)
    if not payload:
        return {
            "worker": "",
            "status": "failed",
            "summary": f"Step {subtask.step_id} 未返回可解析的 Worker 结果",
            "created_files": [],
            "error_code": "INVALID_WORKER_RESULT",
            "error_details": "未找到合法 Worker JSON 输出",
            "tokens": step_tokens,
            "provider": "",
            "model": "",
            "task_type": "",
        }

    result = payload.model_dump()
    result["tokens"] = step_tokens
    spec = WORKER_SPECS.get(payload.worker)
    if spec:
        try:
            runtime = resolve_task_model(spec.task_type)
            result["provider"] = runtime.provider
            result["model"] = runtime.model
        except Exception:
            result["provider"] = ""
            result["model"] = ""
        result["task_type"] = spec.task_type
    else:
        result["provider"] = ""
        result["model"] = ""
        result["task_type"] = ""
    if payload.status == "success" and subtask.tool_hint in ("write", "mixed"):
        missing = find_missing_targets(subtask.target_files, project_context)
        if missing:
            result["status"] = "failed"
            result["error_code"] = "TARGET_NOT_CREATED"
            result["error_details"] = f"目标文件未实际落盘: {', '.join(missing)}"
            result["created_files"] = [path for path in payload.created_files if path not in missing]

    if stream_callback:
        status_icon = "✅" if result["status"] == "success" else "❌"
        stream_callback(f"{status_icon} {result['worker'] or 'worker'}: {result['summary']}\n")
    return result


def execute_plan(
    graph,
    plan,
    project_context: dict,
    route_agent_hint: str,
    thread_id: str,
    stream_callback=None,
) -> tuple[dict[int, dict], list[str], dict | None]:
    step_results: dict[int, dict] = {}
    created_files: list[str] = []

    for subtask in plan.subtasks:
        if not all(dep in step_results and step_results[dep].get("status") == "success" for dep in subtask.depends_on):
            return step_results, created_files, {"subtask": subtask, "error": f"依赖未满足: {subtask.depends_on}"}

        step_result = invoke_subtask(
            graph,
            plan,
            subtask,
            thread_id,
            project_context,
            route_agent_hint=route_agent_hint,
            stream_callback=stream_callback,
        )
        step_results[subtask.step_id] = step_result
        for file_path in step_result.get("created_files", []):
            if file_path not in created_files:
                created_files.append(file_path)

        if step_result.get("status") != "success":
            return step_results, created_files, {"subtask": subtask, "step_result": step_result}

    return step_results, created_files, None
