from __future__ import annotations

from graphs.base import (
    PipelineDefinition,
    PipelineState,
    ensure_project_context,
    finalize_result,
    record_step,
    register_pipeline,
)
from schemas.outputs import SupervisorTask


def run_requirement_workflow(state: PipelineState, services):
    context = ensure_project_context(state, services)
    record_step(state, "plan", "Building supervisor task plan for requirement workflow.")
    tasks = [
        SupervisorTask(
            task_id="plan-data",
            title="定义数据和接口",
            pipeline_name="config_generate",
            description="先梳理系统的数据结构和配置项。",
        ),
        SupervisorTask(
            task_id="impl-logic",
            title="实现核心逻辑",
            pipeline_name="code_generate",
            depends_on=["plan-data"],
            description="在数据结构稳定后实现系统逻辑。",
        ),
        SupervisorTask(
            task_id="impl-tests",
            title="补充测试",
            pipeline_name="test_generate",
            depends_on=["impl-logic"],
            description="为新增逻辑补测试覆盖。",
        ),
    ]
    state["output"] = {
        "project_summary": context.get("summary", ""),
        "plan": [task.model_dump() for task in tasks],
    }
    return finalize_result(
        "requirement_workflow",
        state,
        "success",
        "Generated supervisor plan for the requirement.",
    )


register_pipeline(
    PipelineDefinition(
        key="requirement_workflow",
        title="需求实现",
        category="workflow",
        mode="supervisor",
        description="拆解复杂需求并规划多 Agent 执行顺序。",
        pattern="generate_system",
        input_label="复杂需求",
        placeholder="例如：加一个带蓝耗和施法距离的法杖系统",
        handler=run_requirement_workflow,
    )
)
