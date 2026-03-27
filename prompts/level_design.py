SYSTEM_PROMPT = """你是关卡设计 Agent。
请把需求拆成结构化关卡数据、流程和验证点。"""


def build_prompt(requirement: str, context: str) -> str:
    return f"关卡需求: {requirement}\n上下文:\n{context}\n请输出关卡方案。"
