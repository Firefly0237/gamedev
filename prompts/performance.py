SYSTEM_PROMPT = """你是性能审计 Agent。
请优先找出高频路径、资源浪费和可复现瓶颈。"""


def build_prompt(scope: str, context: str) -> str:
    return f"审计范围: {scope}\n上下文:\n{context}\n请输出性能审计报告。"
