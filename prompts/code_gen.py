SYSTEM_PROMPT = """你是游戏功能实现工程师。
根据需求和项目上下文生成可以继续迭代的代码方案。"""


def build_prompt(requirement: str, context: str) -> str:
    return f"需求: {requirement}\n上下文:\n{context}\n请输出实现方案与候选产物。"
