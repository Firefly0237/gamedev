from __future__ import annotations

import subprocess
from pathlib import Path

from graphs.base import (
    PipelineDefinition,
    PipelineState,
    ensure_project_context,
    finalize_result,
    record_step,
    register_pipeline,
)


def _git_output(project_root: Path, args: list[str]) -> str:
    if not (project_root / ".git").exists():
        return "No git repository found."
    try:
        completed = subprocess.run(["git", *args], cwd=project_root, capture_output=True, text=True, check=True)
        return completed.stdout.strip() or completed.stderr.strip() or "OK"
    except subprocess.CalledProcessError as exc:
        return exc.stderr.strip() or exc.stdout.strip() or str(exc)


def run_precommit_workflow(state: PipelineState, services):
    ensure_project_context(state, services)
    project_root = Path(state["project_root"])
    record_step(state, "git", "Collecting git status and recent commits.")
    state["output"] = {
        "git_status": _git_output(project_root, ["status", "--short"]),
        "git_log": _git_output(project_root, ["log", "--oneline", "-5"]),
        "review_scope": "Run code review and tests before commit.",
    }
    return finalize_result(
        "precommit_workflow",
        state,
        "success",
        "Collected pre-commit review inputs.",
    )


register_pipeline(
    PipelineDefinition(
        key="precommit_workflow",
        title="提交前检查",
        category="workflow",
        mode="supervisor",
        description="汇总 git 状态、代码审查和测试建议。",
        pattern="review_code",
        input_label="提交前检查范围",
        placeholder="例如：检查最近改动并给出提交前建议",
        handler=run_precommit_workflow,
    )
)
