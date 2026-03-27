from __future__ import annotations

from graphs.base import (
    PipelineDefinition,
    PipelineState,
    ensure_project_context,
    finalize_result,
    record_step,
    register_pipeline,
)


def run_level_design(state: PipelineState, services):
    ensure_project_context(state, services)
    record_step(state, "level", "Prepared structured level design scaffold.")
    state["output"] = {
        "requirement": state["user_input"],
        "deliverables": ["关卡 JSON", "流程预览", "设计分析"],
        "sections": ["目标", "节奏", "敌人投放", "奖励和回路"],
    }
    return finalize_result("level_design", state, "success", "Prepared level design scaffold.")


register_pipeline(
    PipelineDefinition(
        key="level_design",
        title="关卡设计",
        category="content",
        mode="react",
        description="将关卡需求拆成结构化设计方案。",
        pattern="generate_content",
        input_label="关卡需求",
        placeholder="例如：设计一个 5 分钟的新手教学关卡",
        handler=run_level_design,
    )
)
