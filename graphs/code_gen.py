from __future__ import annotations

from graphs.base import (
    PipelineDefinition,
    PipelineState,
    ensure_project_context,
    finalize_result,
    record_step,
    register_pipeline,
)


def run_code_generate(state: PipelineState, services):
    context = ensure_project_context(state, services)
    record_step(state, "plan", "Prepared code generation scaffold inputs.")
    state["output"] = {
        "requirement": state["user_input"],
        "context_summary": context.get("summary", ""),
        "suggested_files": [
            "Assets/Scripts/System/NewSystem.cs",
            "Assets/Scripts/System/NewSystemConfig.cs",
            "Assets/Tests/EditMode/NewSystemTests.cs",
        ],
        "next_steps": [
            "定义核心接口和数据结构",
            "补充系统主逻辑",
            "生成测试和文档",
        ],
    }
    return finalize_result("code_generate", state, "success", "Prepared code generation scaffold.")


register_pipeline(
    PipelineDefinition(
        key="code_generate",
        title="代码生成",
        category="code",
        mode="react",
        description="根据需求规划并生成系统代码骨架。",
        pattern="generate_system",
        input_label="代码需求",
        placeholder="例如：生成一个支持堆叠和拖拽的背包系统",
        handler=run_code_generate,
    )
)
