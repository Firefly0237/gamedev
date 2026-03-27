SYSTEM_PROMPT = """你是美术需求生成 Agent。
当图像生成不可用时，输出可直接交付给美术的需求文档。"""


def build_prompt(requirement: str, context: str) -> str:
    return f"美术需求: {requirement}\n上下文:\n{context}\n请输出美术需求文档。"
