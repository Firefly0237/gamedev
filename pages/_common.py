import streamlit as st

from config.logger import logger
from database.db import db


def run_agent(skill_name: str, user_input: str, container=None):
    """Agent Loop 执行"""
    target = container or st

    from config.settings import Settings

    if not Settings.DEEPSEEK_API_KEY:
        target.error("请先在侧边栏配置 API Key")
        return None

    from context.loader import load_skill, match_schema
    from graphs.agent_loop import run_agent_loop

    skill = load_skill(skill_name)
    if not skill:
        target.error(f"Skill '{skill_name}' 未找到")
        return None

    schema = match_schema(user_input)
    project_context = st.session_state.get("project_context", {})
    chat_history = st.session_state.get("chat_history", [])

    logger.info(f"run_agent: skill={skill_name}")
    with target.status("🤖 Agent 执行中...", expanded=True) as status:
        status.write(f"📋 Skill: {skill['name']}")
        status.write("🔧 路径: Agent Loop")

        result = run_agent_loop(
            user_input=user_input,
            skill=skill,
            schema=schema,
            project_context=project_context,
            chat_history=chat_history,
        )

        status.update(
            label=f"{'✅' if result['status'] == 'success' else '❌'} 完成",
            state="complete",
        )

    if result["status"] in ("success", "partial"):
        target.markdown(result.get("display", ""))
        col1, col2, col3 = target.columns(3)
        col1.metric("耗时", f"{result.get('duration', 0):.1f}s")
        col2.metric("Token", f"{result.get('tokens', 0):,}")
        col3.metric("工具调用", f"{result.get('steps', 0)} 次")
    else:
        target.error(f"❌ {result.get('error', '未知错误')}")

    return result


def run_deterministic(skill_name: str, user_input: str, container=None):
    """确定性修改执行"""
    target = container or st

    from config.settings import Settings

    if not Settings.DEEPSEEK_API_KEY:
        target.error("请先在侧边栏配置 API Key")
        return None

    from context.loader import load_skill, match_schema
    from graphs.deterministic import run_code_modify, run_config_modify

    skill = load_skill(skill_name)
    schema = match_schema(user_input)
    project_context = st.session_state.get("project_context", {})

    logger.info(f"run_deterministic: skill={skill_name}")
    with target.status("🔧 确定性执行中...", expanded=True) as status:
        status.write(f"📋 Skill: {skill['name'] if skill else skill_name}")
        status.write("🔧 路径: 确定性修改")

        if skill_name == "modify_config":
            result = run_config_modify(user_input, skill, schema, project_context)
        else:
            result = run_code_modify(user_input, skill, schema, project_context)

        status.update(
            label=f"{'✅' if result['status'] == 'success' else '❌'} 完成",
            state="complete",
        )

    if result["status"] in ("success", "partial"):
        target.markdown(result.get("display", ""))
        col1, col2 = target.columns(2)
        col1.metric("耗时", f"{result.get('duration', 0):.1f}s")
        col2.metric("Token", f"{result.get('tokens', 0):,}")
    else:
        target.error(f"❌ {result.get('error', '未知错误')}")

    return result


def run_with_router(user_input: str) -> dict:
    """聊天入口：Router 分类 → 执行"""
    from graphs.agent_loop import run_agent_loop
    from graphs.deterministic import run_code_modify, run_config_modify
    from graphs.router import classify_intent

    project_context = st.session_state.get("project_context", {})
    chat_history = st.session_state.get("chat_history", [])

    route_result = classify_intent(user_input, project_context)
    route = route_result["route"]
    skill = route_result["skill"]
    schema = route_result["schema"]
    skill_id = route_result["skill_id"]

    logger.info(f"run_with_router: route={route} skill={skill_id}")
    if route == "deterministic":
        if skill_id == "modify_config":
            return run_config_modify(user_input, skill, schema, project_context)
        return run_code_modify(user_input, skill, schema, project_context)

    return run_agent_loop(user_input, skill, schema, project_context, chat_history)
