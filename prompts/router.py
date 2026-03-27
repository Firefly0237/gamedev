SYSTEM_PROMPT = """你是 GameDev 的 Intent Router。
你的任务是根据用户输入识别意图、匹配 Pattern，并选择最合适的下游 Pipeline。
输出必须是 JSON。"""


def build_prompt(user_input: str, available_pipelines: list[str]) -> str:
    pipelines = ", ".join(available_pipelines)
    return (
        f"用户输入: {user_input}\n"
        f"可用 Pipeline: {pipelines}\n"
        "请输出 intent、confidence、matched_pattern、target_pipeline、rationale。"
    )
