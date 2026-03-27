from __future__ import annotations

from graphs.base import (
    PipelineDefinition,
    PipelineState,
    ensure_project_context,
    finalize_result,
    record_step,
    register_pipeline,
)


def run_performance_audit(state: PipelineState, services):
    context = ensure_project_context(state, services)
    record_step(state, "analysis", "Collecting asset size distribution from GameDev MCP tools.")
    asset_sizes = services.mcp.call_tool("scan_asset_sizes", {"project_root": state["project_root"]})
    state["output"] = {
        "scope": state["user_input"],
        "project_summary": context.get("summary", ""),
        "asset_size_distribution": asset_sizes.get("distribution", {}),
        "audit_focus": [
            "频繁执行路径",
            "资源体积异常",
            "同步加载和对象查找",
        ],
    }
    return finalize_result("performance_audit", state, "success", "Prepared performance audit context.")


register_pipeline(
    PipelineDefinition(
        key="performance_audit",
        title="性能审计",
        category="code",
        mode="react",
        description="聚合项目概览与资源分布，输出性能审计入口数据。",
        pattern="analyze_project",
        input_label="审计范围",
        placeholder="例如：审计战斗场景和背包模块的性能热点",
        handler=run_performance_audit,
    )
)
