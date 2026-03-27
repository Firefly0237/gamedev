import streamlit as st


st.header("📜 Git 版本控制")

tab_status, tab_diff, tab_history, tab_commit = st.tabs(["状态", "Diff", "历史", "提交"])

with tab_status:
    repo_path = st.text_input("仓库路径", value=st.session_state.get("project_path", ""), key="git_repo_path")
    if st.button("刷新状态", key="git_status_button", use_container_width=True):
        if repo_path.strip():
            st.info("TODO: 模块六实现")
        else:
            st.warning("请输入仓库路径。")
    st.text_area("Git 状态输出", value="", height=220, disabled=True, placeholder="这里会显示 git status 结果")

with tab_diff:
    diff_target = st.text_input("比较目标", value="HEAD", key="git_diff_target")
    if st.button("查看 Diff", key="git_diff_button", use_container_width=True):
        st.info("TODO: 模块六实现")
    st.text_area("Diff 预览", value="", height=220, disabled=True, placeholder="这里会显示 git diff 结果")

with tab_history:
    history_limit = st.number_input("最近提交数", min_value=1, max_value=50, value=10, step=1)
    if st.button("查看历史", key="git_history_button", use_container_width=True):
        st.info("TODO: 模块六实现")
    st.text_area("提交历史", value="", height=220, disabled=True, placeholder="这里会显示 git log 结果")

with tab_commit:
    commit_message = st.text_input("提交信息", placeholder="feat: add combat balance tool", key="git_commit_message")
    commit_description = st.text_area("提交描述", height=120, placeholder="补充本次提交的背景和影响范围", key="git_commit_description")
    if st.button("创建提交", key="git_commit_button", use_container_width=True):
        if commit_message.strip():
            st.info("TODO: 模块六实现")
        else:
            st.warning("请输入提交信息。")
    st.caption("TODO: 后续模块将接入真实 Git 提交流程。")
