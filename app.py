import json

import streamlit as st

from pages.git_panel import render_git_panel
from pages.skill_page import render_skill_page


def _init_session_state() -> None:
    st.session_state.setdefault("project_context", {})
    st.session_state.setdefault("project_scanned", False)
    st.session_state.setdefault("project_path", "")
    st.session_state.setdefault("detected_genre", "unknown")
    st.session_state.setdefault("chat_history", [])
    st.session_state.setdefault("recommended_skills", [])
    st.session_state.setdefault("example_input", "")
    st.session_state.setdefault("script_list", [])
    st.session_state.setdefault("config_list", [])
    st.session_state.setdefault("pending_plan", None)
    st.session_state.setdefault("restored_task", None)


def _set_query_param(key: str, value: str) -> None:
    st.query_params[key] = value
    st.rerun()


def _normalize_route(route: str) -> str:
    return "orchestrator" if route == "supervisor" else route


def _build_actual_stages(result: dict) -> list[str]:
    """根据执行结果构造实际阶段摘要。"""
    lines = []
    route = _normalize_route(result.get("route", ""))

    if result.get("status") == "awaiting_approval":
        lines.append(f"📋 已生成 {len(result.get('actions', []))} 步执行计划")
        lines.append("✋ 等待你确认后再真正改文件")
        return lines

    if route == "orchestrator":
        actions = result.get("actions", [])
        if actions:
            lines.append(f"📋 拆解为 {len(actions)} 个子任务")
        output_files = result.get("output_files", [])
        if output_files:
            lines.append(f"🔨 已生成 {len(output_files)} 个文件")
    elif route == "deterministic":
        actions = result.get("actions", [])
        if actions:
            success = sum(1 for action in actions if action.get("success"))
            lines.append(f"🔧 修改 {success}/{len(actions)} 项")
    elif route == "agent_loop":
        steps = result.get("steps", 0)
        if steps:
            lines.append(f"🛠 调用工具 {steps} 次")

    verif = result.get("verification", {})
    if verif.get("performed"):
        if verif.get("passed"):
            lines.append("✔️ 验证通过")
        else:
            fail_count = sum(1 for detail in verif.get("details", []) if not detail.get("passed"))
            lines.append(f"⚠️ 验证未通过 ({fail_count} 项)")

    return lines


def _render_pending_plan() -> None:
    handle = st.session_state.get("pending_plan")
    if not handle:
        return

    from graphs.orchestrator import resume_orchestrator
    from pages._task_card import render_task_card

    plan_actions = handle.get("actions", [])
    thread_id = handle.get("thread_id", "pending")

    st.info("📋 多文件任务已生成计划。确认后才会真正执行并修改文件。")
    with st.expander(f"📋 执行计划（{len(plan_actions)} 步，等待确认）", expanded=True):
        for action in plan_actions:
            files = action.get("files", [])
            st.markdown(f"- **Step {action.get('step_id', '?')}**: {action.get('description', '')}")
            if files:
                st.caption(f"文件: {', '.join(files)}")

        col1, col2 = st.columns(2)
        if col1.button("✅ 执行计划", use_container_width=True, key=f"approve_{thread_id}"):
            with st.chat_message("assistant"):
                stream_box = st.empty()
                chunks: list[str] = []

                def on_chunk(text: str):
                    chunks.append(text)
                    stream_box.markdown("".join(chunks) + "▌")

                with st.status("🔨 按计划执行中...", expanded=True) as status:
                    result = resume_orchestrator(handle, approved=True, stream_callback=on_chunk)
                    for stage_text in _build_actual_stages(result):
                        status.write(stage_text)
                    if result["status"] == "success":
                        status.update(label="✅ 完成", state="complete")
                    elif result["status"] == "partial":
                        status.update(label="⚠️ 部分完成", state="error")
                    else:
                        status.update(label="❌ 失败", state="error")

                if chunks:
                    stream_box.markdown("".join(chunks))
                render_task_card(result)
                response = result.get("summary") or result.get("display", "")[:200]
                st.session_state.chat_history.append({"role": "assistant", "content": response})

            st.session_state["pending_plan"] = None

        if col2.button("❌ 取消", use_container_width=True, key=f"cancel_{thread_id}"):
            result = resume_orchestrator(handle, approved=False)
            st.session_state["pending_plan"] = None
            st.session_state.chat_history.append({"role": "assistant", "content": result.get("display", "已取消")})
            st.info("已取消。你可以修改需求后重新发起。")


def _render_restored_task() -> None:
    restored = st.session_state.get("restored_task")
    if not restored:
        return

    from pages._task_card import render_task_card

    st.info("📜 这是从执行历史恢复的任务结果。")
    render_task_card(restored)
    if st.button("关闭历史任务视图", use_container_width=False, key="close_restored_task"):
        st.session_state["restored_task"] = None
        st.rerun()


def _list_skill_options(skill_genre: str) -> list[tuple[str, str]]:
    from context.loader import list_skills, load_skill

    options = []
    for skill_name in list_skills(skill_genre):
        skill = load_skill(skill_name)
        if not skill:
            continue
        options.append((skill_name, skill.get("name", skill_name)))
    return options


def _render_skill_buttons(skill_genre: str, fallback: list[tuple[str, str]]) -> None:
    options = _list_skill_options(skill_genre)
    if options:
        for skill_name, label in options:
            if st.button(label, use_container_width=True, key=f"skill_{skill_genre}_{skill_name}"):
                _set_query_param("skill", skill_name)
        return

    for skill_name, label in fallback:
        if st.button(label, use_container_width=True, key=f"fallback_{skill_genre}_{skill_name}"):
            _set_query_param("skill", skill_name)


def render_chat() -> None:
    for msg in st.session_state.chat_history:
        st.chat_message(msg["role"]).write(msg["content"])

    _render_pending_plan()
    _render_restored_task()

    if not st.session_state.chat_history and not st.session_state.project_scanned:
        st.markdown("### 💬 有什么可以帮你？")
        st.caption("扫描一个 Unity 项目后，我能更好地帮你。也可以直接提问。")

        examples = [
            "审查 PlayerController 的性能问题",
            "把火焰剑攻击力改到150",
            "为 DamageCalculator 生成测试",
        ]
        cols = st.columns(len(examples))
        for col, example in zip(cols, examples):
            if col.button(example, use_container_width=True, key=f"example_{example}"):
                st.session_state.example_input = example

    user_input = st.chat_input("输入你的需求...", disabled=bool(st.session_state.get("pending_plan")))
    if not user_input and st.session_state.example_input:
        user_input = st.session_state.example_input
        st.session_state.example_input = ""

    if user_input:
        rerun_for_pending_plan = False
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)

        with st.chat_message("assistant"):
            from config.settings import Settings

            if not Settings.DEEPSEEK_API_KEY:
                response = "请先在侧边栏的 ⚙️ API 设置中配置 DeepSeek API Key。"
                st.write(response)
            else:
                from pages._common import run_with_router
                from graphs.router import classify_intent
                from pages._task_card import get_route_stages, render_task_card

                project_context = st.session_state.get("project_context", {})
                try:
                    route_hint = classify_intent(user_input, project_context)
                    route_name = route_hint.get("route", "agent_loop")
                except Exception:
                    route_name = "agent_loop"

                with st.status("🤖 执行中...", expanded=True) as status:
                    stages = get_route_stages(route_name)
                    if stages:
                        status.write(f"{stages[0][1]} {stages[0][2]}")

                    stream_box = st.empty()
                    chunks: list[str] = []

                    def on_chunk(text: str):
                        chunks.append(text)
                        stream_box.markdown("".join(chunks) + "▌")

                    result = run_with_router(user_input, stream_callback=on_chunk)

                    actual_stages = _build_actual_stages(result)
                    for stage_text in actual_stages:
                        status.write(stage_text)

                    if result["status"] == "awaiting_approval":
                        status.update(label="✋ 等待确认", state="complete")
                    elif result["status"] == "success":
                        status.update(label="✅ 完成", state="complete")
                    elif result["status"] == "partial":
                        status.update(label="⚠️ 部分完成", state="error")
                    else:
                        status.update(label="❌ 失败", state="error")

                if chunks:
                    stream_box.markdown("".join(chunks))

                if result["status"] == "awaiting_approval":
                    st.session_state["pending_plan"] = result
                    response = f"已生成执行计划：{result.get('summary', '')}。请先确认。"
                    st.info(response)
                    rerun_for_pending_plan = True
                else:
                    # [后续8] 原展示代码已被 render_task_card 替换，如需回滚参考 git 历史
                    render_task_card(result)
                    response = result.get("summary") or result.get("display", "")[:200]

        st.session_state.chat_history.append({"role": "assistant", "content": response})
        if rerun_for_pending_plan:
            st.rerun()


def main() -> None:
    st.set_page_config(page_title="GameDev", page_icon="🎮", layout="wide")
    _init_session_state()

    with st.sidebar:
        st.title("🎮 GameDev")
        from config.settings import Settings

        with st.expander("⚙️ API 设置", expanded=False):
            st.text_input("DeepSeek API Key", type="password", key="api_key")
            st.text_input("Base URL", value="https://api.deepseek.com/v1", key="api_base_url")

        project_path = st.text_input(
            "项目路径",
            value=st.session_state.project_path,
            placeholder="输入 Unity 项目路径",
        )
        st.session_state.project_path = project_path

        if st.button("🔍 扫描项目", use_container_width=True):
            if not project_path:
                st.error("请输入项目路径")
            else:
                from dataclasses import asdict

                from database.db import db
                from mcp_tools.mcp_client import init_mcp
                from scanner.unity_scanner import UnityScanner

                scanner = UnityScanner(project_path)
                valid, msg = scanner.validate_project()
                if valid:
                    with st.spinner("扫描中..."):
                        ctx = scanner.scan()
                        ctx_dict = asdict(ctx)

                        st.session_state.project_context = ctx_dict
                        st.session_state.project_scanned = True
                        st.session_state.project_path = project_path
                        st.session_state.detected_genre = ctx.detected_genre
                        st.session_state.script_list = scanner.get_script_list()
                        st.session_state.config_list = scanner.get_config_list()
                        st.session_state.recommended_skills = scanner.get_recommended_skills(ctx)

                        try:
                            init_mcp(project_path)
                        except Exception as exc:
                            st.warning(f"MCP 启动部分失败: {exc}")

                        db.save_project_context(project_path, ctx_dict, ctx.total_scripts)

                    st.success(
                        f"✅ {ctx.total_scripts} 脚本 | {len(ctx.scenes)} 场景 | 类型: {ctx.detected_genre}"
                    )
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

        if st.session_state.project_scanned:
            col1, col2 = st.columns(2)
            col1.metric("脚本数", st.session_state.project_context.get("total_scripts", 0))
            col2.metric("场景数", len(st.session_state.project_context.get("scenes", [])))
            st.caption(f"🎮 {st.session_state.detected_genre}")

            ctx_dict = st.session_state.get("project_context", {})
            coverage = ctx_dict.get("test_coverage_ratio", 0)
            covered_count = len(ctx_dict.get("covered_classes", []))
            uncovered_count = len(ctx_dict.get("uncovered_scripts", []))
            total_coverable = covered_count + uncovered_count
            if total_coverable > 0:
                if coverage >= 0.7:
                    st.caption(f"📊 测试覆盖: {coverage:.0%} ({covered_count}/{total_coverable}) ✅")
                elif coverage >= 0.3:
                    st.caption(f"📊 测试覆盖: {coverage:.0%} ({covered_count}/{total_coverable}) ⚠️")
                else:
                    st.caption(f"📊 测试覆盖: {coverage:.0%} ({covered_count}/{total_coverable}) 🔴")
            else:
                st.caption("📊 测试覆盖: 暂无可测试脚本")

            from mcp_tools.mcp_client import get_mcp_status, get_unity_status

            try:
                mcp_status = get_mcp_status()
                if mcp_status:
                    icons = " ".join("🟢" if value else "🔴" for value in mcp_status.values())
                    st.caption(f"MCP: {icons}")
                else:
                    st.caption("MCP: 🔴")
            except Exception:
                st.caption("MCP: 🔴")
            unity_status = get_unity_status()
            if unity_status.get("connected"):
                tool_count = len(unity_status.get("tool_names", []))
                st.caption(f"Unity MCP: Coplay ✅ ({tool_count} tools)")
            elif ctx_dict.get("unity_mcp_package_installed"):
                reason = unity_status.get("reason") or "请确认 Unity Editor 已打开 MCP for Unity 并允许连接"
                st.caption(f"Unity MCP: Coplay ⚠️ 未连接 ({reason})")
            else:
                st.caption("Unity MCP: Coplay 未安装，编译/测试验证已降级为语法检查")

            if not unity_status.get("connected"):
                with st.expander("如何启用 Unity 编译/测试"):
                    st.markdown(
                        """
1. 在 Unity 项目中安装 CoplayDev 包：
   `https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main`
2. 打开 `Window > MCP for Unity`
3. 启动 MCP Server，并确认显示已连接
4. 在 GameDev 所在环境安装 `uv`，以便通过 `uvx` 启动 Coplay stdio server

可选：
- 如果要更严格的脚本校验，可在 Unity 中按 Coplay 文档安装 Roslyn 依赖
- 如果只做代码审查而不做编译/测试，当前降级行为是正常的
                        """
                    )
            st.divider()

            st.subheader("📌 推荐操作")
            from database.db import db
            from pages._disclosure import compute_dynamic_recommendations

            dynamic_recs = compute_dynamic_recommendations(
                project_context=ctx_dict,
                chat_history=st.session_state.get("chat_history", []),
                task_logs=db.get_recent_tasks(10),
            )
            if dynamic_recs:
                for rec in dynamic_recs:
                    if st.button(rec["label"], use_container_width=True, key=f"rec_{rec['skill']}_{rec['weight']}"):
                        _set_query_param("skill", rec["skill"])
                    st.caption(rec["reason"])
            else:
                defaults = [
                    ("review_code", "🔍 代码审查", "检查项目中的脚本质量和性能问题"),
                    ("modify_config", "📊 配置修改", "快速调整 JSON 配置数值"),
                    ("generate_test", "🧪 测试生成", "为现有脚本生成 NUnit 测试"),
                ]
                for skill_name, label, reason in defaults:
                    if st.button(label, use_container_width=True, key=f"default_{skill_name}"):
                        _set_query_param("skill", skill_name)
                    st.caption(reason)

        with st.expander("📦 更多功能", expanded=False):
            st.subheader("🔧 通用")
            common_fallback = [
                ("review_code", "代码审查"),
                ("modify_config", "配置修改"),
                ("modify_code", "代码修改"),
                ("generate_system", "系统实现"),
                ("generate_test", "测试生成"),
                ("generate_shader", "Shader"),
                ("generate_ui", "UI"),
                ("generate_editor_tool", "Editor工具"),
                ("translate", "本地化"),
                ("analyze_deps", "依赖分析"),
                ("analyze_perf", "性能分析"),
                ("summarize_requirement", "需求拆解"),
            ]
            _render_skill_buttons("common", common_fallback)

            detected_genre = st.session_state.detected_genre
            if detected_genre != "unknown":
                st.subheader(f"🎮 {detected_genre} 专用")
                _render_skill_buttons(detected_genre, [])

        if st.button("📜 Git", use_container_width=True, key="git_panel_btn"):
            _set_query_param("view", "git")

        with st.expander("📋 执行历史", expanded=False):
            from database.db import db

            tasks = db.get_recent_tasks(10)
            if tasks:
                for task in tasks:
                    emoji = {"success": "✅", "failed": "❌", "running": "⏳"}.get(task["status"], "❓")
                    label = f"{emoji} [{task['pipeline_type']}] {task['created_at'][:16]}"
                    if st.button(label, use_container_width=True, key=f"task_{task['id']}"):
                        payload = task.get("result_json") or ""
                        if payload:
                            st.session_state["restored_task"] = json.loads(payload)
                            st.rerun()
                        else:
                            st.warning("这条历史记录没有保存完整结果快照。")
                stats = db.get_task_stats()
                st.caption(f"总计 {stats['total']} 次 | Token {stats['total_tokens']:,}")
            else:
                st.caption("暂无执行记录")

    skill_name = st.query_params.get("skill")
    view = st.query_params.get("view")

    if skill_name:
        render_skill_page(skill_name)
    elif view == "git":
        render_git_panel()
    else:
        render_chat()


if __name__ == "__main__":
    main()
