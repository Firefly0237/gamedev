from __future__ import annotations

from graphs.base import (
    PipelineDefinition,
    PipelineState,
    ensure_project_context,
    finalize_result,
    record_step,
    register_pipeline,
)


def run_localization(state: PipelineState, services):
    ensure_project_context(state, services)
    record_step(state, "localization", "Prepared localization scaffold.")
    state["output"] = {
        "task": state["user_input"],
        "rules": ["保护 {placeholder}", "保持 key 不变", "尽量保留原句语气"],
        "suggested_output": "Localization.generated.json",
    }
    return finalize_result("localization", state, "success", "Prepared localization scaffold.")


register_pipeline(
    PipelineDefinition(
        key="localization",
        title="本地化",
        category="content",
        mode="fixed",
        description="为多语言内容生成翻译工作骨架。",
        pattern="translate_content",
        input_label="本地化任务",
        placeholder="例如：把 UI 语言表翻译成英文和日文",
        handler=run_localization,
    )
)
