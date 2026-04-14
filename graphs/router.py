from config.logger import logger
from context.loader import load_skill, match_schema, match_skill
from schemas.contracts import default_safety_policy, infer_task_type, infer_validator

BATCH_KEYWORDS = ["所有", "全部", "批量", "都"]
MODIFY_HINTS = ["改", "修改", "调整", "更改", "提升", "提高", "降低", "涨价", "降价", "增加", "减少", "翻倍"]


def is_batch_modify(user_input: str, skill_id: str) -> bool:
    if skill_id != "modify_config":
        return False
    return any(keyword in user_input for keyword in BATCH_KEYWORDS)


def should_fallback_to_config_modify(user_input: str, skill, schema: dict | None) -> bool:
    if skill or not schema:
        return False
    return any(hint in user_input for hint in MODIFY_HINTS)


def classify_intent(user_input: str, project_context: dict = None) -> dict:
    """三分叉分类：deterministic / agent_loop / supervisor"""

    detected_genre = (project_context or {}).get("detected_genre", "unknown")

    skill = match_skill(user_input, detected_genre)
    schema = match_schema(user_input)
    if should_fallback_to_config_modify(user_input, skill, schema):
        skill = load_skill("modify_config")
    skill_id = skill["skill_id"] if skill else ""

    route = "agent_loop"
    if skill_id in ("modify_config", "modify_code"):
        route = "deterministic"
    elif skill_id in ("generate_system", "summarize_requirement"):
        route = "supervisor"

    task_type = infer_task_type(skill_id)
    is_batch = is_batch_modify(user_input, skill_id)
    if is_batch:
        validator = "ConfigBatchPlan"
    else:
        validator = infer_validator(skill_id)

    safety_policy = default_safety_policy(task_type)
    if is_batch:
        safety_policy["diff_preview"] = True
        safety_policy["require_confirm"] = True

    logger.info(f"Router: '{user_input[:30]}...' → {route} | Skill={skill_id} | task_type={task_type}")

    return {
        "route": route,
        "skill": skill,
        "schema": schema,
        "skill_id": skill_id,
        "task_type": task_type,
        "validator": validator,
        "safety_policy": safety_policy,
        "is_batch": is_batch,
    }
