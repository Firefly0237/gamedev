from __future__ import annotations

import streamlit as st

from graphs import list_pipelines, run_pipeline
from graphs.base import create_services
from graphs.router import route_input
from pages._common import (
    get_cached_project_context,
    refresh_project_context,
    render_pipeline_result,
    resolve_project_root,
)
from schemas.outputs import PipelineResult


@st.cache_resource
def get_services():
    return create_services()


st.set_page_config(page_title="GameDev", page_icon="🎮", layout="wide")

services = get_services()

with st.sidebar:
    st.title("GameDev")
    project_root = st.text_input("项目路径", value=resolve_project_root(), key="sidebar_project_root")
    st.session_state["project_root"] = project_root
    if st.button("刷新项目扫描"):
        context = refresh_project_context(project_root)
        st.session_state["sidebar_project_context"] = context

    context = st.session_state.get("sidebar_project_context") or get_cached_project_context(project_root)
    if context:
        metadata = context.get("metadata", {})
        st.caption(context.get("summary", ""))
        st.write(f"脚本数: {metadata.get('script_count', 0)}")
        st.write(f"场景数: {metadata.get('scene_count', 0)}")
        st.write(f"配置数: {metadata.get('config_count', 0)}")

    st.markdown("**MCP 状态**")
    st.json(services.mcp.list_tools())

    st.markdown("**手动模块**")
    for pipeline in list_pipelines():
        st.write(f"- {pipeline.title}")

st.title("GameDev")
st.caption("AI 驱动的游戏研发工作台骨架。聊天入口用于自动路由，左侧多页面用于手动模式。")

with st.form("chat_form"):
    user_input = st.text_area("聊天入口", placeholder="例如：做一个背包系统", height=160)
    submitted = st.form_submit_button("执行")

if submitted and user_input.strip():
    decision = route_input(user_input, services)
    result = run_pipeline(
        pipeline_name=decision.target_pipeline,
        user_input=user_input,
        project_root=project_root,
        matched_pattern=decision.matched_pattern,
        intent=decision.intent,
        services=services,
    )
    st.session_state["chat_decision"] = decision.model_dump()
    st.session_state["chat_result"] = result.model_dump()

decision_payload = st.session_state.get("chat_decision")
if decision_payload:
    st.subheader("路由结果")
    st.json(decision_payload)

chat_result = st.session_state.get("chat_result")
if chat_result:
    render_pipeline_result(PipelineResult.model_validate(chat_result))

st.subheader("执行历史")
history = services.db.list_recent_tasks(limit=10)
if history:
    st.dataframe(history, use_container_width=True)
else:
    st.info("暂无执行记录。")
