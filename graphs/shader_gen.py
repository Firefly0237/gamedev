from __future__ import annotations

from graphs.base import (
    PipelineDefinition,
    PipelineState,
    ensure_project_context,
    finalize_result,
    record_step,
    register_pipeline,
)


def run_shader_generate(state: PipelineState, services):
    ensure_project_context(state, services)
    record_step(state, "shader", "Prepared shader generation brief.")
    state["output"] = {
        "effect_description": state["user_input"],
        "suggested_shader_file": "Assets/Shaders/NewEffect.shader",
        "sections": ["Properties", "SubShader", "Pass", "HLSLPROGRAM"],
    }
    return finalize_result("shader_generate", state, "success", "Prepared shader generation scaffold.")


register_pipeline(
    PipelineDefinition(
        key="shader_generate",
        title="Shader 生成",
        category="code",
        mode="fixed",
        description="将效果描述转成 Shader 设计骨架。",
        pattern="generate_content",
        input_label="效果描述",
        placeholder="例如：做一个边缘发光的魔法护盾 Shader",
        handler=run_shader_generate,
    )
)
