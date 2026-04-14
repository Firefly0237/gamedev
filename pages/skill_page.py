def render_skill_page(skill_name: str):
    import streamlit as st
    from pathlib import Path

    skills_root = Path("context/skills")
    skill_file = None
    for md_file in skills_root.rglob(f"{skill_name}.md"):
        skill_file = md_file
        break

    if not skill_file:
        st.error(f"Skill '{skill_name}' 未找到")
        if st.button("↩️ 返回"):
            st.query_params.clear()
            st.rerun()
        return

    content = skill_file.read_text(encoding="utf-8")
    first_line = content.split("\n")[0].lstrip("# ").strip()
    parent_dir = skill_file.parent.name

    st.header(f"📋 {first_line}")
    badge = "🔧 通用" if parent_dir == "common" else f"🎮 {parent_dir}"
    st.caption(f"{badge} | Skill: {skill_name}")

    user_input = st.text_area("描述你的需求", height=120, key=f"input_{skill_name}")

    if skill_name in ("modify_config", "modify_code"):
        files = st.session_state.get("config_list", []) + st.session_state.get("script_list", [])
        if files:
            selected = st.selectbox("选择目标文件（可选）", [""] + files, key=f"file_{skill_name}")
            if selected:
                user_input = f"[文件:{selected}] {user_input}"

    if skill_name == "review_code":
        scripts = st.session_state.get("script_list", [])
        if scripts:
            selected = st.selectbox("选择要审查的脚本", scripts, key="review_file")
            user_input = selected

    if skill_name == "generate_test":
        ctx = st.session_state.get("project_context", {})
        uncovered = ctx.get("uncovered_scripts", [])
        all_scripts = st.session_state.get("script_list", [])

        if uncovered:
            uncovered_paths = [s.get("path", "") for s in uncovered if s.get("path")]
            st.info(f"📊 检测到 {len(uncovered_paths)} 个脚本未覆盖测试")

            mode = st.radio(
                "选择模式",
                ["从未覆盖列表选择", "从全部脚本选择", "手动输入"],
                horizontal=True,
                key="gen_test_mode",
            )

            if mode == "从未覆盖列表选择":
                selected_files = st.multiselect(
                    "选择要生成测试的脚本",
                    uncovered_paths,
                    default=uncovered_paths[:1],
                    key="gen_test_uncovered",
                )
                if selected_files:
                    user_input = "为以下脚本生成测试: " + ", ".join(selected_files)
            elif mode == "从全部脚本选择":
                selected_files = st.multiselect(
                    "选择要生成测试的脚本",
                    all_scripts,
                    key="gen_test_all",
                )
                if selected_files:
                    user_input = "为以下脚本生成测试: " + ", ".join(selected_files)
        else:
            if all_scripts:
                selected = st.selectbox(
                    "选择要生成测试的脚本",
                    all_scripts,
                    key="gen_test_select",
                )
                if selected:
                    user_input = f"为 {selected} 生成测试"

    if skill_name == "translate":
        langs = st.multiselect(
            "目标语言",
            ["en", "ja", "ko", "fr", "de", "es", "pt", "ru"],
            default=["en"],
            key="langs",
        )
        if langs:
            user_input = f"{user_input} → {','.join(langs)}"

    col1, col2 = st.columns([3, 1])
    with col1:
        run = st.button("🚀 执行", use_container_width=True, type="primary", key=f"run_{skill_name}")
    with col2:
        if st.button("↩️ 返回", use_container_width=True, key=f"back_{skill_name}"):
            st.query_params.clear()
            st.rerun()

    if run:
        if not user_input or not user_input.strip():
            st.warning("请输入需求")
        else:
            from pages._common import run_agent, run_deterministic

            container = st.container()
            if skill_name in ("modify_config", "modify_code"):
                run_deterministic(skill_name, user_input, container)
            else:
                run_agent(skill_name, user_input, container)
