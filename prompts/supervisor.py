SYSTEM_PROMPT = """你是多 Agent Supervisor。
你的职责是拆解任务、按依赖顺序调度，并对结果做评估。"""


def build_prompt(requirement: str, context: str) -> str:
    return f"复杂需求: {requirement}\n上下文:\n{context}\n请输出阶段计划。"
