SYSTEM_PROMPT = """你是剧情与对话设计 Agent。
请保持角色口吻一致，并输出结构化对话树。"""


def build_prompt(requirement: str, context: str) -> str:
    return f"剧情需求: {requirement}\n上下文:\n{context}\n请输出对话树方案。"
