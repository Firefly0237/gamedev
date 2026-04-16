from __future__ import annotations

from langgraph_supervisor import create_supervisor

from agents.llm import create_llm
from config.settings import Settings
from .workers import ALL_SPECS, get_all_agents


def _build_supervisor_prompt() -> str:
    lines = ["你是 GameDev Supervisor，负责把单个已批准子任务交给最合适的 Worker。", "", "## 可用 Worker"]
    for spec in ALL_SPECS:
        status = "可用" if spec.enabled else "占位 stub"
        lines.append(f"- {spec.name} [{status}]：{spec.description}")

    lines.extend(
        [
            "",
            "## 规则",
            "1. 每次只能 handoff 给一个 Worker。",
            "2. 你自己不能写代码，也不能直接调用项目工具。",
            "3. Worker 的最终回复必须是 JSON；你要根据其中的 status / error_code 判断是否完成。",
            "4. 遇到 NOT_IMPLEMENTED 或 DOMAIN_MISMATCH 时，可以改派其他 Worker；否则优先结束并把失败留给外层处理。",
            "5. 当前只处理用户消息中的这一个子任务，不要扩展到其他步骤。",
            "6. Worker 成功后直接 finish，不要继续 handoff。",
            f"7. 单个子任务最多尝试 {Settings.MAX_HANDOFFS_PER_TASK} 次 handoff，避免死循环。",
        ]
    )
    return "\n".join(lines)


def build_supervisor_graph(checkpointer):
    llm = create_llm(task_type="routing", temperature=0)
    return create_supervisor(
        agents=get_all_agents(),
        model=llm,
        prompt=_build_supervisor_prompt(),
        output_mode="last_message",
        parallel_tool_calls=False,
        include_agent_name="inline",
    ).compile(checkpointer=checkpointer)
