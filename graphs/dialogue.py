from __future__ import annotations

from graphs.base import (
    PipelineDefinition,
    PipelineState,
    ensure_project_context,
    finalize_result,
    record_step,
    register_pipeline,
)


def run_dialogue_generate(state: PipelineState, services):
    ensure_project_context(state, services)
    record_step(state, "dialogue", "Prepared dialogue tree scaffold.")
    state["output"] = {
        "scene_requirement": state["user_input"],
        "deliverables": ["对话树 JSON", "配套 C# 结构", "角色语气约束"],
        "rules": ["保持已有角色口吻", "节点 ID 递增", "显式标记分支条件"],
    }
    return finalize_result("dialogue_generate", state, "success", "Prepared dialogue generation scaffold.")


register_pipeline(
    PipelineDefinition(
        key="dialogue_generate",
        title="对话剧情",
        category="content",
        mode="fixed",
        description="根据剧情需求生成对话树骨架。",
        pattern="generate_content",
        input_label="剧情需求",
        placeholder="例如：继续铁匠和玩家的任务对话",
        handler=run_dialogue_generate,
    )
)
