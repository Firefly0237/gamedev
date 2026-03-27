SYSTEM_PROMPT = """你是资深游戏客户端代码审查工程师。
优先发现行为错误、性能风险、生命周期问题和缺失测试。"""


def build_prompt(target: str, context: str) -> str:
    return f"目标: {target}\n上下文:\n{context}\n请输出问题列表。"
