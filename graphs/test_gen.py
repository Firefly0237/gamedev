from __future__ import annotations

from graphs.base import (
    PipelineDefinition,
    PipelineState,
    ensure_project_context,
    finalize_result,
    record_step,
    register_pipeline,
)


def run_test_generate(state: PipelineState, services):
    ensure_project_context(state, services)
    record_step(state, "test-plan", "Prepared NUnit test scaffolding plan.")
    state["output"] = {
        "target": state["user_input"],
        "suggested_test_file": "Assets/Tests/EditMode/GeneratedTests.cs",
        "test_cases": [
            "初始化状态",
            "主要成功路径",
            "边界条件",
            "错误输入",
        ],
    }
    return finalize_result("test_generate", state, "success", "Prepared test generation scaffold.")


register_pipeline(
    PipelineDefinition(
        key="test_generate",
        title="测试生成",
        category="code",
        mode="fixed",
        description="为已有逻辑生成 NUnit 测试骨架。",
        pattern="generate_system",
        input_label="测试目标",
        placeholder="例如：为 InventoryService 生成 NUnit 测试",
        handler=run_test_generate,
    )
)
