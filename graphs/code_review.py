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


RISK_RULES = [
    ("FindObjectOfType", "medium", "运行时频繁查找对象可能造成性能浪费。"),
    ("Resources.Load", "medium", "同步资源加载应确认调用频率和缓存策略。"),
    ("Update(", "low", "Update 中逻辑需关注频率和空引用保护。"),
    ("catch (", "medium", "捕获异常后需要确认是否存在吞异常。"),
]


def run_code_review(state: PipelineState, services):
    ensure_project_context(state, services)
    params = state.get("params", {})
    file_path = params.get("file_path", "")
    findings: list[dict[str, str | int]] = []
    if file_path:
        target = Path(state["project_root"]) / file_path
        if target.exists():
            content = target.read_text(encoding="utf-8", errors="ignore")
            for marker, severity, description in RISK_RULES:
                line_no = next((idx for idx, line in enumerate(content.splitlines(), start=1) if marker in line), None)
                if line_no:
                    findings.append(
                        {
                            "severity": severity,
                            "title": f"检测到 {marker}",
                            "description": description,
                            "file_path": file_path,
                            "line": line_no,
                        }
                    )
            record_step(state, "review", f"Reviewed {file_path} with heuristic rules.")
        else:
            state.setdefault("warnings", []).append(f"Target file not found: {file_path}")
    else:
        record_step(state, "review", "No file specified; returning review checklist.", status="completed")
    state["output"] = {
        "target_file": file_path,
        "findings": findings,
        "checklist": [
            "检查生命周期方法中的空引用和频繁分配",
            "检查异步、协程和事件解绑",
            "补充行为回归和测试覆盖",
        ],
    }
    return finalize_result("code_review", state, "success", "Prepared code review result.")


register_pipeline(
    PipelineDefinition(
        key="code_review",
        title="代码审查",
        category="code",
        mode="react",
        description="对脚本进行风险导向的审查。",
        pattern="review_code",
        input_label="审查目标",
        placeholder="例如：审查 Assets/Scripts/PlayerController.cs",
        handler=run_code_review,
    )
)
