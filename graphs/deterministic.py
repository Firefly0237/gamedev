import json
import time
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import create_llm
from config.logger import logger
from config.settings import Settings
from context.loader import build_system_prompt
from database.db import db
from graphs.safety import normalize_path, safe_write_file
from mcp_tools.mcp_client import call_mcp_tool, get_project_path
from schemas.outputs import CodeModifyPlan, ConfigModifyPlan, try_parse


def _extract_total_tokens(response) -> int:
    usage = response.response_metadata.get("token_usage", {}) if getattr(response, "response_metadata", None) else {}
    if "total_tokens" in usage:
        return usage["total_tokens"] or 0
    usage2 = getattr(response, "usage_metadata", None) or {}
    return usage2.get("total_tokens", 0) or 0


def _resolve_project_path(project_context: dict | None) -> str:
    return get_project_path() or (project_context or {}).get("project_path", "")


def _build_code_modify_system(user_input: str, skill: dict, schema: dict, project_context: dict) -> str:
    system = build_system_prompt(skill, schema, project_context)
    project_path = _resolve_project_path(project_context)
    user_lower = user_input.lower()

    candidates: list[str] = []
    for script in (project_context or {}).get("scripts", []):
        path = script.get("path", "")
        class_name = script.get("class_name", "")
        stem = Path(path).stem.lower() if path else ""
        if class_name and class_name.lower() in user_lower:
            candidates.append(path)
        elif stem and stem in user_lower:
            candidates.append(path)
        elif path and path.lower() in user_lower:
            candidates.append(path)

    extra_parts: list[str] = []
    for rel_path in list(dict.fromkeys(candidates))[:2]:
        try:
            content = call_mcp_tool("read_file", {"path": normalize_path(rel_path, project_path)})
            extra_parts.append(f"## 目标文件原文\n文件: {rel_path}\n```csharp\n{content[:8000]}\n```")
        except Exception as exc:
            logger.warning(f"读取代码上下文失败: {rel_path} ({exc})")

    if extra_parts:
        system += "\n\n" + "\n\n".join(extra_parts)
    return system


def run_config_modify(user_input: str, skill: dict, schema: dict, project_context: dict) -> dict:
    """配置修改完整流程"""
    t0 = time.time()
    task_id = db.log_task_start("modify_config", user_input[:200])

    system = build_system_prompt(skill, schema, project_context)
    llm = create_llm(task_type="generation", temperature=0.1)
    total_tokens = 0

    plan = None
    last_error = ""
    for attempt in range(Settings.MAX_RETRIES):
        messages = [SystemMessage(content=system)]
        if attempt == 0:
            messages.append(HumanMessage(content=user_input))
        else:
            messages.append(
                HumanMessage(
                    content=(
                        f"{user_input}\n\n上次输出格式错误: {last_error}\n"
                        "请严格按照输出格式示例输出纯 JSON。"
                    )
                )
            )

        resp = llm.invoke(messages)
        total_tokens += _extract_total_tokens(resp)

        result, err = try_parse(resp.content, ConfigModifyPlan)
        if result:
            plan = result
            break

        last_error = err
        logger.warning(f"ConfigModify 第{attempt + 1}次解析失败: {err}")

    if not plan:
        duration = time.time() - t0
        db.log_task_end(task_id, "failed", total_tokens, duration, last_error)
        return {
            "status": "failed",
            "error": f"解析失败（{Settings.MAX_RETRIES}次）: {last_error}",
            "tokens": total_tokens,
            "duration": duration,
        }

    project_path = _resolve_project_path(project_context)
    results = []

    for action in plan.actions:
        full_path = normalize_path(action.file_path, project_path)
        try:
            raw = call_mcp_tool("read_file", {"path": full_path})
            data = json.loads(raw)

            items = data if isinstance(data, list) else data.get("items", data.get("data", [data]))
            if not isinstance(items, list):
                items = [items]

            found = False
            for item in items:
                if str(item.get(action.match_field)) == str(action.match_value):
                    current = item.get(action.target_field)
                    if str(current) != str(action.old_value):
                        results.append(
                            {
                                "file": action.file_path,
                                "success": False,
                                "error": f"old_value 不匹配: 期望 {action.old_value}，实际 {current}",
                            }
                        )
                        found = True
                        break

                    item[action.target_field] = action.new_value
                    found = True
                    break

            if not found:
                results.append(
                    {
                        "file": action.file_path,
                        "success": False,
                        "error": f"未找到 {action.match_field}={action.match_value}",
                    }
                )
                continue

            new_json = json.dumps(data, ensure_ascii=False, indent=2)
            write_result = safe_write_file(full_path, new_json, project_path)
            results.append(
                {
                    "file": action.file_path,
                    "field": action.target_field,
                    "old": action.old_value,
                    "new": action.new_value,
                    "success": write_result["success"],
                    "error": write_result.get("error", ""),
                }
            )
        except Exception as exc:
            results.append({"file": action.file_path, "success": False, "error": str(exc)})

    success_count = sum(1 for result in results if result.get("success"))
    status = "success" if success_count == len(results) else ("partial" if success_count > 0 else "failed")

    display = f"## 配置修改结果\n\n{plan.summary}\n\n"
    for result in results:
        if result.get("success"):
            display += f"✅ {result['file']}: {result['field']} {result['old']} → {result['new']}\n"
        else:
            display += f"❌ {result.get('file', '?')}: {result.get('error', '未知错误')}\n"

    duration = time.time() - t0
    db.log_task_end(task_id, status, total_tokens, duration)
    return {
        "status": status,
        "display": display,
        "tokens": total_tokens,
        "results": results,
        "duration": duration,
    }


def run_code_modify(user_input: str, skill: dict, schema: dict, project_context: dict) -> dict:
    """代码修改完整流程"""
    t0 = time.time()
    task_id = db.log_task_start("modify_code", user_input[:200])

    system = _build_code_modify_system(user_input, skill, schema, project_context)
    llm = create_llm(task_type="generation", temperature=0.1)
    total_tokens = 0

    plan = None
    last_error = ""
    for attempt in range(Settings.MAX_RETRIES):
        messages = [SystemMessage(content=system)]
        if attempt == 0:
            messages.append(HumanMessage(content=user_input))
        else:
            messages.append(
                HumanMessage(content=f"{user_input}\n\n上次格式错误: {last_error}\n请严格输出纯 JSON。")
            )

        resp = llm.invoke(messages)
        total_tokens += _extract_total_tokens(resp)

        result, err = try_parse(resp.content, CodeModifyPlan)
        if result:
            plan = result
            break

        last_error = err
        logger.warning(f"CodeModify 第{attempt + 1}次解析失败: {err}")

    if not plan:
        duration = time.time() - t0
        db.log_task_end(task_id, "failed", total_tokens, duration, last_error)
        return {"status": "failed", "error": f"解析失败: {last_error}", "tokens": total_tokens, "duration": duration}

    project_path = _resolve_project_path(project_context)
    results = []

    for action in plan.actions:
        full_path = normalize_path(action.file_path, project_path)
        try:
            content = call_mcp_tool("read_file", {"path": full_path})
            count = content.count(action.search_pattern)
            if count == 0:
                results.append({"file": action.file_path, "success": False, "error": "search_pattern 在文件中未找到"})
                continue
            if count > 1:
                results.append(
                    {
                        "file": action.file_path,
                        "success": False,
                        "error": f"search_pattern 匹配到 {count} 处，需要唯一匹配",
                    }
                )
                continue

            new_content = content.replace(action.search_pattern, action.replace_with, 1)
            write_result = safe_write_file(full_path, new_content, project_path)
            results.append(
                {
                    "file": action.file_path,
                    "success": write_result["success"],
                    "error": write_result.get("error", ""),
                    "search": action.search_pattern[:50],
                    "replace": action.replace_with[:50],
                }
            )
        except Exception as exc:
            results.append({"file": action.file_path, "success": False, "error": str(exc)})

    success_count = sum(1 for result in results if result.get("success"))
    status = "success" if success_count == len(results) else ("partial" if success_count > 0 else "failed")

    display = f"## 代码修改结果\n\n{plan.summary}\n\n"
    for result in results:
        if result.get("success"):
            display += f"✅ {result['file']}: `{result['search']}` → `{result['replace']}`\n"
        else:
            display += f"❌ {result.get('file', '?')}: {result.get('error', '')}\n"

    duration = time.time() - t0
    db.log_task_end(task_id, status, total_tokens, duration)
    return {"status": status, "display": display, "tokens": total_tokens, "duration": duration, "results": results}
