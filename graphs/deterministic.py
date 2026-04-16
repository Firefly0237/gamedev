import json
import time
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import create_llm, get_llm_runtime_info
from config.logger import logger
from config.settings import Settings
from context.loader import build_system_prompt, extract_focus_class
from database.db import db
from graphs.safety import normalize_path, safe_write_file
from mcp_tools.mcp_client import call_mcp_tool, get_project_path
from schemas.contracts import empty_result
from schemas.outputs import CodeModifyPlan, ConfigBatchPlan, ConfigModifyPlan, try_parse


def _single_model_usage(task_type: str, llm_info, tokens: int) -> list[dict]:
    return [
        {
            "role": "deterministic",
            "task_type": task_type,
            "provider": llm_info.provider if llm_info else "",
            "model": llm_info.model if llm_info else "",
            "tokens": tokens,
        }
    ]


def _extract_total_tokens(response) -> int:
    usage = response.response_metadata.get("token_usage", {}) if getattr(response, "response_metadata", None) else {}
    if "total_tokens" in usage:
        return usage["total_tokens"] or 0
    usage2 = getattr(response, "usage_metadata", None) or {}
    return usage2.get("total_tokens", 0) or 0


def _resolve_project_path(project_context: dict | None) -> str:
    return get_project_path() or (project_context or {}).get("project_path", "")


def _build_code_modify_system(user_input: str, skill: dict, schema: dict, project_context: dict) -> str:
    focus = extract_focus_class(user_input, project_context or {})
    system = build_system_prompt(skill, schema, project_context, focus_class=focus)
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

    focus = extract_focus_class(user_input, project_context or {})
    system = build_system_prompt(skill, schema, project_context, focus_class=focus)
    llm = create_llm(task_type="intent_parse", temperature=0.1)
    llm_info = get_llm_runtime_info(llm)
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
        db.log_task_end(
            task_id,
            "failed",
            total_tokens,
            duration,
            last_error,
            provider=llm_info.provider if llm_info else "",
            model=llm_info.model if llm_info else "",
        )
        result = empty_result(route="deterministic", task_id=task_id)
        result["status"] = "failed"
        result["error"] = f"解析失败（{Settings.MAX_RETRIES}次）: {last_error}"
        result["display"] = f"❌ {result['error']}"
        result["tokens"] = total_tokens
        result["duration"] = duration
        return result

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

    summary = plan.summary
    display = f"## 配置修改结果\n\n{summary}\n\n"
    output_files = []
    for result in results:
        if result.get("success"):
            display += f"✅ {result['file']}: {result['field']} {result['old']} → {result['new']}\n"
            if result.get("file") and result["file"] not in output_files:
                output_files.append(result["file"])
        else:
            display += f"❌ {result.get('file', '?')}: {result.get('error', '未知错误')}\n"

    duration = time.time() - t0
    result = empty_result(route="deterministic", task_id=task_id)
    result["status"] = status
    result["display"] = display
    result["summary"] = summary
    result["output_files"] = output_files
    result["actions"] = results
    result["tokens"] = total_tokens
    result["duration"] = duration
    result["model_usage"] = _single_model_usage("intent_parse", llm_info, total_tokens)
    if status == "failed":
        failures = [item.get("error", "") for item in results if item.get("error")]
        result["error"] = failures[0] if failures else "配置修改失败"
    db.log_task_end(
        task_id,
        status,
        total_tokens,
        duration,
        result["error"],
        provider=llm_info.provider if llm_info else "",
        model=llm_info.model if llm_info else "",
    )
    return result


def run_config_batch(user_input: str, skill: dict, schema: dict, project_context: dict) -> dict:
    """批量配置修改流程"""
    t0 = time.time()
    task_id = db.log_task_start("modify_config_batch", user_input[:200])

    focus = extract_focus_class(user_input, project_context or {})
    system = build_system_prompt(skill, schema, project_context, focus_class=focus)
    llm = create_llm(task_type="intent_parse", temperature=0.1)
    llm_info = get_llm_runtime_info(llm)
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
                        "请严格按照 ConfigBatchPlan 输出纯 JSON。"
                    )
                )
            )

        resp = llm.invoke(messages)
        total_tokens += _extract_total_tokens(resp)

        result, err = try_parse(resp.content, ConfigBatchPlan)
        if result:
            plan = result
            break

        last_error = err
        logger.warning(f"ConfigBatch 第{attempt + 1}次解析失败: {err}")

    if not plan:
        duration = time.time() - t0
        db.log_task_end(
            task_id,
            "failed",
            total_tokens,
            duration,
            last_error,
            provider=llm_info.provider if llm_info else "",
            model=llm_info.model if llm_info else "",
        )
        result = empty_result(route="deterministic", task_id=task_id)
        result["status"] = "failed"
        result["error"] = f"批量修改解析失败: {last_error}"
        result["display"] = f"❌ {result['error']}"
        result["tokens"] = total_tokens
        result["duration"] = duration
        return result

    project_path = _resolve_project_path(project_context)
    all_changes = []
    output_files = []

    for action in plan.actions:
        full_path = normalize_path(action.file_path, project_path)
        try:
            raw = call_mcp_tool("read_file", {"path": full_path})
            data = json.loads(raw)

            items = data if isinstance(data, list) else data.get("items", data.get("data", [data]))
            if not isinstance(items, list):
                items = [items]

            filtered = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                if not action.filter:
                    filtered.append(item)
                    continue

                matched = all(str(item.get(key)) == str(value) for key, value in action.filter.items())
                if matched:
                    filtered.append(item)

            if not filtered:
                all_changes.append(
                    {
                        "file": action.file_path,
                        "success": False,
                        "error": f"filter {action.filter} 未匹配任何记录",
                    }
                )
                continue

            for item in filtered:
                if action.target_field not in item:
                    all_changes.append(
                        {
                            "file": action.file_path,
                            "match": str(item.get("name", item.get("id", "?")))[:30],
                            "success": False,
                            "error": f"字段不存在: {action.target_field}",
                        }
                    )
                    continue

                old_value = item[action.target_field]
                if action.operation == "multiply":
                    new_value = type(old_value)(float(old_value) * float(action.value))
                elif action.operation == "add":
                    new_value = type(old_value)(float(old_value) + float(action.value))
                else:
                    new_value = action.value

                item[action.target_field] = new_value
                all_changes.append(
                    {
                        "file": action.file_path,
                        "match": str(item.get("name", item.get("id", "?")))[:30],
                        "field": action.target_field,
                        "old": old_value,
                        "new": new_value,
                        "success": True,
                    }
                )

            new_json = json.dumps(data, ensure_ascii=False, indent=2)
            write_result = safe_write_file(full_path, new_json, project_path)
            if write_result["success"] and action.file_path not in output_files:
                output_files.append(action.file_path)
            elif not write_result["success"]:
                all_changes.append(
                    {
                        "file": action.file_path,
                        "success": False,
                        "error": write_result.get("error", "写回失败"),
                    }
                )
        except Exception as exc:
            all_changes.append({"file": action.file_path, "success": False, "error": str(exc)})

    success_count = sum(1 for change in all_changes if change.get("success"))
    total_count = len(all_changes)
    if success_count == 0:
        status = "failed"
    elif success_count == total_count:
        status = "success"
    else:
        status = "partial"

    display = f"## 批量配置修改\n\n**{plan.summary}**\n\n"
    display += f"共影响 {success_count} 条记录\n\n"

    success_changes = [change for change in all_changes if change.get("success")]
    failed_changes = [change for change in all_changes if not change.get("success")]

    if success_changes:
        display += "### 变更明细（前 5 条）\n\n"
        for change in success_changes[:5]:
            display += f"- ✅ {change.get('match', '?')}: {change['field']} {change['old']} → {change['new']}\n"
        if len(success_changes) > 5:
            display += f"- ... 还有 {len(success_changes) - 5} 条变更\n"

    if failed_changes:
        display += "\n### 失败项\n\n"
        for change in failed_changes:
            display += f"- ❌ {change.get('file', '?')}: {change.get('error', '')}\n"

    duration = time.time() - t0

    result = empty_result(route="deterministic", task_id=task_id)
    result["status"] = status
    result["display"] = display
    result["summary"] = plan.summary
    result["output_files"] = output_files
    result["actions"] = all_changes
    result["tokens"] = total_tokens
    result["duration"] = duration
    result["model_usage"] = _single_model_usage("intent_parse", llm_info, total_tokens)
    if status == "failed":
        failures = [item.get("error", "") for item in all_changes if item.get("error")]
        result["error"] = failures[0] if failures else "批量配置修改失败"
    db.log_task_end(
        task_id,
        status,
        total_tokens,
        duration,
        result["error"],
        provider=llm_info.provider if llm_info else "",
        model=llm_info.model if llm_info else "",
    )
    return result


def run_code_modify(user_input: str, skill: dict, schema: dict, project_context: dict) -> dict:
    """代码修改完整流程"""
    t0 = time.time()
    task_id = db.log_task_start("modify_code", user_input[:200])

    system = _build_code_modify_system(user_input, skill, schema, project_context)
    llm = create_llm(task_type="intent_parse", temperature=0.1)
    llm_info = get_llm_runtime_info(llm)
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
        db.log_task_end(
            task_id,
            "failed",
            total_tokens,
            duration,
            last_error,
            provider=llm_info.provider if llm_info else "",
            model=llm_info.model if llm_info else "",
        )
        result = empty_result(route="deterministic", task_id=task_id)
        result["status"] = "failed"
        result["error"] = f"解析失败（{Settings.MAX_RETRIES}次）: {last_error}"
        result["display"] = f"❌ {result['error']}"
        result["tokens"] = total_tokens
        result["duration"] = duration
        return result

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
    output_files = []
    for result in results:
        if result.get("success"):
            display += f"✅ {result['file']}: `{result['search']}` → `{result['replace']}`\n"
            if result["file"] not in output_files:
                output_files.append(result["file"])
        else:
            display += f"❌ {result.get('file', '?')}: {result.get('error', '')}\n"

    result = empty_result(route="deterministic", task_id=task_id)
    result["status"] = status
    result["display"] = display
    result["summary"] = plan.summary
    result["output_files"] = output_files
    result["actions"] = results
    result["tokens"] = total_tokens
    result["duration"] = time.time() - t0
    result["model_usage"] = _single_model_usage("intent_parse", llm_info, total_tokens)

    cs_files = [file_path for file_path in output_files if file_path.endswith(".cs")]
    if cs_files and status in ("success", "partial"):
        from graphs.verify import verify_files

        verify_result = verify_files(
            files=cs_files,
            project_context=project_context,
            mode=Settings.DEFAULT_VERIFY_MODE,
            skill_id="modify_code",
        )
        result["verification"] = verify_result

        if not verify_result["passed"]:
            result["status"] = "partial"
            fail_msgs = "\n".join(
                f"  - {detail['message']}"
                for detail in verify_result["details"]
                if not detail["passed"]
            )
            result["display"] += f"\n\n### ⚠️ 修改后验证未通过\n{fail_msgs}\n\n如需修复，请再次描述需要修改的内容。"
            result["error"] = "修改后验证未通过"

    if status == "failed":
        failures = [item.get("error", "") for item in results if item.get("error")]
        result["error"] = failures[0] if failures else "代码修改失败"

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
