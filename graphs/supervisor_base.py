from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict

from schemas.outputs import SupervisorPlan, SupervisorTask


class SupervisorState(TypedDict, total=False):
    requirement: str
    project_root: str
    tasks: list[dict[str, Any]]
    journal: list[dict[str, Any]]
    evaluation_notes: list[str]


def build_supervisor_plan(requirement: str, tasks: list[SupervisorTask], notes: list[str] | None = None) -> SupervisorPlan:
    return SupervisorPlan(
        requirement=requirement,
        tasks=tasks,
        evaluation_notes=notes or [],
    )
