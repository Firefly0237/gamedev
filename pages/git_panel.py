import streamlit as st

from pages._common import resolve_project_root, run_git


st.title("Git 面板")
st.caption("读取当前仓库的状态、差异和最近提交。")

project_root = st.text_input("项目路径", value=resolve_project_root(), key="git_panel_project_root")
st.session_state["project_root"] = project_root

if st.button("刷新 Git 信息"):
    st.session_state["git_panel_status"] = {
        "status": run_git(project_root, ["status", "--short"]),
        "diff": run_git(project_root, ["diff", "--", "."]),
        "log": run_git(project_root, ["log", "--oneline", "-10"]),
    }

payload = st.session_state.get("git_panel_status")
if payload:
    st.markdown("**git status**")
    st.code(payload["status"] or "(empty)")
    st.markdown("**git diff**")
    st.code(payload["diff"] or "(empty)")
    st.markdown("**git log**")
    st.code(payload["log"] or "(empty)")
