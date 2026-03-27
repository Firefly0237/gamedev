SYSTEM_PROMPT = """你是 Shader 工程师。
请将效果描述拆分为渲染目标、参数和 Shader 实现结构。"""


def build_prompt(effect_description: str, context: str) -> str:
    return f"效果描述: {effect_description}\n上下文:\n{context}\n请输出 Shader 设计。"
