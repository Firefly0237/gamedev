from __future__ import annotations

from graphs.base import (
    PipelineDefinition,
    PipelineState,
    ensure_project_context,
    finalize_result,
    record_step,
    register_pipeline,
)


def run_asset_generate(state: PipelineState, services):
    ensure_project_context(state, services)
    record_step(state, "art", "Prepared art generation brief.")
    state["output"] = {
        "requirement": state["user_input"],
        "deliverables": ["风格说明", "尺寸和用途", "分层需求", "导出规范"],
        "fallback_mode": "文档优先，图像生成接口后续接入",
    }
    return finalize_result("asset_generate", state, "success", "Prepared art generation scaffold.")


register_pipeline(
    PipelineDefinition(
        key="asset_generate",
        title="资产生成",
        category="art",
        mode="fixed",
        description="生成图片资源需求文档或图像生成参数。",
        pattern="generate_content",
        input_label="美术需求",
        placeholder="例如：生成一张火焰法杖图标的美术需求",
        handler=run_asset_generate,
    )
)
