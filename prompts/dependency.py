SYSTEM_PROMPT = """你是资源依赖分析 Agent。
请从引用链、资源体积和潜在风险三个维度分析。"""


def build_prompt(target: str, context: str) -> str:
    return f"分析目标: {target}\n上下文:\n{context}\n请输出依赖分析。"
