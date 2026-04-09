from config.logger import logger
from context.loader import match_schema, match_skill


def classify_intent(user_input: str, project_context: dict = None) -> dict:
    """三分叉分类：deterministic / agent_loop / supervisor"""

    detected_genre = (project_context or {}).get("detected_genre", "unknown")

    skill = match_skill(user_input, detected_genre)
    schema = match_schema(user_input)
    skill_id = skill["skill_id"] if skill else ""

    route = "agent_loop"
    if skill_id in ("modify_config", "modify_code"):
        route = "deterministic"
    elif skill_id in ("generate_system", "summarize_requirement"):
        route = "supervisor"

    logger.info(f"Router: '{user_input[:30]}...' → {route} | Skill={skill_id}")

    return {
        "route": route,
        "skill": skill,
        "schema": schema,
        "skill_id": skill_id,
    }
