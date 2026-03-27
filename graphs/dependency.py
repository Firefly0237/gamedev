from __future__ import annotations

from pathlib import Path

from graphs.base import (
    PipelineDefinition,
    PipelineState,
    ensure_project_context,
    finalize_result,
    record_step,
    register_pipeline,
)


def run_dependency_analysis(state: PipelineState, services):
    ensure_project_context(state, services)
    params = state.get("params", {})
    target = params.get("target", state["user_input"])
    result = {"target": target, "meta": None, "references": []}
    if str(target).endswith(".meta"):
        meta = services.mcp.call_tool("parse_meta_file", {"path": str(Path(state["project_root"]) / target)})
        result["meta"] = meta
        guid = meta.get("guid")
        if guid:
            refs = services.mcp.call_tool("find_references", {"project_root": state["project_root"], "guid": guid})
            result["references"] = refs.get("matches", [])
    record_step(state, "dependency", "Prepared dependency analysis data.")
    state["output"] = result
    return finalize_result("dependency_analysis", state, "success", "Prepared dependency analysis scaffold.")


register_pipeline(
    PipelineDefinition(
        key="dependency_analysis",
        title="资源依赖",
        category="content",
        mode="fixed",
        description="分析资源或脚本的引用关系。",
        pattern="analyze_project",
        input_label="依赖分析目标",
        placeholder="例如：分析 Assets/Prefabs/Player.prefab.meta 的引用关系",
        handler=run_dependency_analysis,
    )
)
