"""统一的任务卡片渲染组件。

支持三种展示类型：
- step_card: 从 actions 渲染结构化步骤（deterministic/orchestrator）
- content_card: 直接展示 display markdown（agent_loop）
- simple_card: 失败或空结果的简化展示

所有卡片共享相同的 Header 和 Footer，只有主体不同。
"""

from typing import Any

import streamlit as st


def _normalize_route(route: str) -> str:
    return "orchestrator" if route == "supervisor" else route


def render_task_card(result: dict, container=None):
    """渲染任务卡片。"""
    target = container or st

    route = _normalize_route(result.get("route", ""))
    status = result.get("status", "failed")

    if status == "failed" and not result.get("output_files") and not result.get("actions"):
        _render_simple_card(result, target)
        return

    if route in ("deterministic", "orchestrator"):
        _render_step_card(result, target)
    else:
        _render_content_card(result, target)


def _status_icon(status: str) -> str:
    return {
        "success": "✅",
        "partial": "⚠️",
        "failed": "❌",
    }.get(status, "❓")


def _route_badge(route: str) -> str:
    route = _normalize_route(route)
    return {
        "deterministic": "🔧 确定性",
        "agent_loop": "🤖 Agent",
        "orchestrator": "🧭 Orchestrator",
        "none": "❓",
    }.get(route, route)


def _verification_badge(verification: dict) -> str:
    if not verification or not verification.get("performed"):
        return "➖ 未验证"
    if verification.get("passed"):
        return "✅ 验证通过"
    return "⚠️ 验证未通过"


def _render_card_header(result: dict, target):
    """卡片头部：状态图标 + summary + 徽章。"""
    status = result.get("status", "failed")
    summary = result.get("summary", "") or "任务"
    icon = _status_icon(status)

    target.markdown(f"### {icon} {summary}")

    badge_cols = target.columns(3)
    badge_cols[0].caption(_route_badge(result.get("route", "")))
    badge_cols[1].caption(_verification_badge(result.get("verification", {})))
    badge_cols[2].caption(f"⏱ {result.get('duration', 0):.1f}s")

    output_files = result.get("output_files", [])
    if output_files:
        target.caption(f"📁 生成 {len(output_files)} 个文件")


def _render_card_footer(result: dict, target):
    """卡片尾部：输出文件 + metric + 验证详情 + 影响范围。"""
    output_files = result.get("output_files", [])
    if output_files:
        with target.expander(f"📁 输出文件 ({len(output_files)})", expanded=False):
            for file_path in output_files:
                st.caption(f"- {file_path}")

    verif = result.get("verification", {})
    if verif.get("performed") and verif.get("details"):
        has_failures = any(not detail.get("passed") for detail in verif["details"])
        with target.expander(
            f"🔍 验证详情 ({len(verif['details'])} 项)",
            expanded=has_failures,
        ):
            for detail in verif["details"]:
                emoji = "✅" if detail.get("passed") else "❌"
                type_label = detail.get("type", "check")
                msg = detail.get("message", "")[:200]
                st.caption(f"{emoji} [{type_label}] {msg}")

    if result.get("route") == "deterministic" and output_files:
        _render_impact_analysis(output_files, target)

    metric_cols = target.columns(3)
    metric_cols[0].caption(f"🔤 {result.get('tokens', 0):,} token")
    metric_cols[1].caption(f"🧩 {result.get('steps', 0)} 步")
    if result.get("task_id"):
        metric_cols[2].caption(f"📝 #{result['task_id']}")


def _render_impact_analysis(output_files: list, target):
    """展示修改某类可能影响的文件。"""
    project_context = st.session_state.get("project_context", {})
    reverse_graph = project_context.get("reverse_graph", {})
    class_to_path = project_context.get("class_to_path", {})

    if not reverse_graph or not class_to_path:
        return

    impacted = set()
    for output_file in output_files:
        for cls, path in class_to_path.items():
            if path == output_file or output_file.endswith(path):
                try:
                    from scanner.reference_graph import get_impact_scope

                    scope = get_impact_scope(cls, reverse_graph, depth=2)
                    for impacted_class in scope:
                        if impacted_class in class_to_path:
                            impacted.add(class_to_path[impacted_class])
                except Exception:
                    pass

    if impacted:
        with target.expander(f"⚠️ 可能受影响的文件 ({len(impacted)})", expanded=False):
            for file_path in list(impacted)[:10]:
                st.caption(f"- {file_path}")
            if len(impacted) > 10:
                st.caption(f"... 还有 {len(impacted) - 10} 个")


def _render_step_card(result: dict, target):
    _render_card_header(result, target)

    actions = result.get("actions", [])
    route = result.get("route", "")

    if result.get("display"):
        with target.expander("📋 执行详情", expanded=False):
            target.markdown(result["display"][:4000])

    if actions:
        title = "📝 计划步骤" if route == "orchestrator" else "🧩 修改详情"
        with target.expander(f"{title} ({len(actions)} 项)", expanded=False):
            if route == "orchestrator":
                _render_orchestrator_steps(actions, result, target)
            else:
                _render_deterministic_actions(actions, result, target)

    if result.get("error"):
        target.error(f"❌ {result['error'][:300]}")

    _render_card_footer(result, target)


def _render_orchestrator_steps(actions: list, result: dict, target):
    """Orchestrator 的 SubTask 列表展示。"""
    for index, action in enumerate(actions):
        step_id = action.get("step_id", index + 1)
        description = action.get("description", "")
        files = action.get("files", action.get("target_files", []))
        _render_single_orchestrator_step(step_id, description, files, target)


def _render_single_orchestrator_step(step_id: Any, description: str, files: list, target):
    files_str = f" → {', '.join(files[:2])}" if files else ""
    if len(files) > 2:
        files_str += f" (+{len(files) - 2})"
    target.markdown(f"- ✅ **Step {step_id}**: {description[:100]}{files_str}")


def _render_deterministic_actions(actions: list, result: dict, target):
    """Deterministic 的 action 列表展示。"""
    success_count = sum(1 for action in actions if action.get("success"))
    total = len(actions)

    target.caption(f"🔧 修改项 ({success_count}/{total})")
    for action in actions:
        _render_single_deterministic_action(action, target)


def _render_single_deterministic_action(action: dict, target):
    success = action.get("success")
    emoji = "✅" if success else "❌"

    if "match" in action and "field" in action:
        target.markdown(
            f"- {emoji} {action['match']}: **{action['field']}** {action.get('old', '?')} → {action.get('new', '?')}"
        )
    elif "field" in action and "old" in action:
        file_label = action.get("file", "?")
        target.markdown(
            f"- {emoji} `{file_label}`: **{action['field']}** {action['old']} → {action['new']}"
        )
    elif "search" in action and "replace" in action:
        file_label = action.get("file", "?")
        search = action["search"][:40]
        replace = action["replace"][:40]
        target.markdown(f"- {emoji} `{file_label}`: `{search}` → `{replace}`")
    else:
        target.markdown(f"- {emoji} {str(action)[:150]}")

    if not success and action.get("error"):
        target.caption(f"  ⚠️ {action['error'][:200]}")


def _render_content_card(result: dict, target):
    _render_card_header(result, target)

    display = result.get("display", "")
    if display:
        preview = display[:280]
        target.markdown(preview + ("..." if len(display) > 280 else ""))
        if len(display) > 280:
            with target.expander("📋 展开完整内容", expanded=False):
                target.markdown(display)
    else:
        target.caption("（无输出内容）")

    if result.get("error"):
        target.error(f"❌ {result['error'][:300]}")

    _render_card_footer(result, target)


def _render_simple_card(result: dict, target):
    icon = _status_icon(result.get("status", "failed"))
    summary = result.get("summary", "") or "任务失败"

    target.markdown(f"### {icon} {summary}")
    target.caption(_route_badge(result.get("route", "")))

    if result.get("error"):
        target.error(f"❌ {result['error'][:500]}")
    elif result.get("display"):
        target.markdown(result["display"][:800])

    cols = target.columns(3)
    cols[0].caption(f"⏱ {result.get('duration', 0):.1f}s")
    cols[1].caption(f"🔤 {result.get('tokens', 0):,} token")
    cols[2].caption(_verification_badge(result.get("verification", {})))


def get_route_stages(route: str) -> list[tuple]:
    """返回 route 的预测性阶段文案。"""
    if route == "deterministic":
        return [
            (0.0, "🔍", "正在解析修改意图..."),
            (1.5, "🔧", "正在执行修改..."),
            (3.0, "✔️", "正在验证结果..."),
        ]
    if _normalize_route(route) == "orchestrator":
        return [
            (0.0, "📋", "正在拆解任务..."),
            (5.0, "🎯", "规划完成，开始执行子任务..."),
            (15.0, "🔨", "正在生成文件..."),
            (30.0, "✔️", "正在验证和修复..."),
        ]
    if route == "agent_loop":
        return [
            (0.0, "🤖", "正在分析需求..."),
            (2.0, "🔧", "正在调用工具..."),
            (5.0, "📝", "正在生成输出..."),
            (10.0, "✔️", "正在验证..."),
        ]
    return [(0.0, "⏳", "处理中...")]
