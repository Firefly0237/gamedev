from __future__ import annotations

from graphs.base import (
    PipelineDefinition,
    PipelineState,
    ensure_project_context,
    finalize_result,
    record_step,
    register_pipeline,
)


def run_config_generate(state: PipelineState, services):
    context = ensure_project_context(state, services)
    schema = state.get("context", {}).get("project_schema", {})
    record_step(state, "config", "Prepared config generation scaffold.")
    state["output"] = {
        "requirement": state["user_input"],
        "project_summary": context.get("summary", ""),
        "matched_schema": schema,
        "suggested_outputs": [
            "JSON 配置文件",
            "对应的 C# 数据类",
        ],
    }
    return finalize_result("config_generate", state, "success", "Prepared config generation scaffold.")


register_pipeline(
    PipelineDefinition(
        key="config_generate",
        title="配置生成",
        category="content",
        mode="fixed",
        description="为策划配置和数据类生成骨架。",
        pattern="generate_content",
        input_label="配置需求",
        placeholder="例如：生成武器配置表和 WeaponConfig 数据类",
        handler=run_config_generate,
    )
)
