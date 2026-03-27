SYSTEM_PROMPT = """你是本地化 Agent。
请保证 key、占位符和变量标签不变。"""


def build_prompt(requirement: str, context: str) -> str:
    return f"本地化任务: {requirement}\n上下文:\n{context}\n请输出翻译方案。"
