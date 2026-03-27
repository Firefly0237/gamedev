SYSTEM_PROMPT = """你是负责自动化测试的工程师。
你的重点是为现有逻辑生成合理的 NUnit 测试结构。"""


def build_prompt(target: str, context: str) -> str:
    return f"测试目标: {target}\n上下文:\n{context}\n请输出测试建议。"
