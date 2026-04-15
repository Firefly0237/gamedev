from pathlib import Path

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


def _read_skill_title(md_path: Path) -> str:
    try:
        content = md_path.read_text(encoding="utf-8")
    except OSError:
        return md_path.stem

    first_line = content.splitlines()[0] if content else md_path.stem
    return first_line.lstrip("# ").strip() or md_path.stem


def _set_query_param(key: str, value: str) -> None:
    st.query_params[key] = value
    st.rerun()


def _build_actual_stages(result: dict) -> list[str]:
    """根据执行结果构造实际阶段摘要。"""
    lines = []
    route = result.get("route", "")

    if route == "supervisor":
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


def _render_skill_buttons(skill_dir: Path, fallback: list[tuple[str, str]]) -> None:
    if skill_dir.exists():
        md_files = sorted(skill_dir.glob("*.md"))
    else:
        md_files = []

    if md_files:
        for md_file in md_files:
            skill_name = md_file.stem
            label = _read_skill_title(md_file)
            if st.button(label, use_container_width=True, key=f"skill_{skill_name}"):
                _set_query_param("skill", skill_name)
    else:
        for skill_name, label in fallback:
            if st.button(label, use_container_width=True, key=f"fallback_{skill_name}"):
                _set_query_param("skill", skill_name)


def render_chat() -> None:
    for msg in st.session_state.chat_history:
        st.chat_message(msg["role"]).write(msg["content"])

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

    user_input = st.chat_input("输入你的需求...")
    if not user_input and st.session_state.example_input:
        user_input = st.session_state.example_input
        st.session_state.example_input = ""

    if user_input:
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

                    result = run_with_router(user_input)

                    actual_stages = _build_actual_stages(result)
                    for stage_text in actual_stages:
                        status.write(stage_text)

                    if result["status"] == "success":
                        status.update(label="✅ 完成", state="complete")
                    elif result["status"] == "partial":
                        status.update(label="⚠️ 部分完成", state="error")
                    else:
                        status.update(label="❌ 失败", state="error")

                # [后续8] 原展示代码已被 render_task_card 替换，如需回滚参考 git 历史
                render_task_card(result)
                response = result.get("summary") or result.get("display", "")[:200]

        st.session_state.chat_history.append({"role": "assistant", "content": response})


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

            from mcp_tools.mcp_client import get_mcp_status

            try:
                mcp_status = get_mcp_status()
                if mcp_status:
                    icons = " ".join("🟢" if value else "🔴" for value in mcp_status.values())
                    st.caption(f"MCP: {icons}")
                else:
                    st.caption("MCP: 🔴")
            except Exception:
                st.caption("MCP: 🔴")

            if not Settings.is_unity_available():
                st.caption("⚠️ Unity 未配置：编译/测试验证已降级为语法检查")
                with st.expander("如何配置 Unity"):
                    st.markdown(
                        """
1. 安装 Unity（任意版本）
2. 在 .env 中设置 UNITY_EXECUTABLE_PATH，例如：

```env
# Windows
UNITY_EXECUTABLE_PATH=C:/Program Files/Unity/Hub/Editor/2022.3.10f1/Editor/Unity.exe

# macOS
UNITY_EXECUTABLE_PATH=/Applications/Unity/Hub/Editor/2022.3.10f1/Unity.app/Contents/MacOS/Unity
```

3. 重启 GameDev
                        """
                    )
            st.divider()

            st.subheader("📌 推荐操作")
            if st.session_state.recommended_skills:
                for rec in st.session_state.recommended_skills:
                    if st.button(rec["label"], use_container_width=True, key=f"rec_{rec['skill']}"):
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
            _render_skill_buttons(Path("context/skills/common"), common_fallback)

            detected_genre = st.session_state.detected_genre
            if detected_genre != "unknown":
                st.subheader(f"🎮 {detected_genre} 专用")
                _render_skill_buttons(Path("context/skills") / detected_genre, [])

        if st.button("📜 Git", use_container_width=True, key="git_panel_btn"):
            _set_query_param("view", "git")

        with st.expander("📋 执行历史", expanded=False):
            from database.db import db

            tasks = db.get_recent_tasks(10)
            if tasks:
                for task in tasks:
                    emoji = {"success": "✅", "failed": "❌", "running": "⏳"}.get(task["status"], "❓")
                    st.text(f"{emoji} [{task['pipeline_type']}] {task['created_at'][:16]}")
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
