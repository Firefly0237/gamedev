SYSTEM_PROMPT = """你是游戏策划数据工程师。
请生成稳定、可维护的数据结构与配置样例。"""


def build_prompt(requirement: str, context: str) -> str:
    return f"配置需求: {requirement}\n上下文:\n{context}\n请输出配置设计。"
