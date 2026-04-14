from typing import Literal, TypedDict


RouteName = Literal["deterministic", "agent_loop", "supervisor"]
TaskType = Literal["modify", "review", "generate", "analyze", "translate"]


class SafetyPolicy(TypedDict):
    auto_backup: bool
    git_auto_save: bool
    require_confirm: bool
    diff_preview: bool


class RouterResult(TypedDict):
    route: RouteName
    skill: dict | None
    schema: dict | None
    skill_id: str
    task_type: TaskType
    validator: str | None
    safety_policy: SafetyPolicy


class VerificationDetail(TypedDict):
    type: str
    passed: bool
    message: str


class VerificationResult(TypedDict):
    performed: bool
    passed: bool
    details: list[VerificationDetail]


class ExecutionResult(TypedDict):
    status: Literal["success", "partial", "failed"]
    route: str
    display: str
    summary: str
    output_files: list[str]
    actions: list[dict]
    steps: int
    verification: VerificationResult
    tokens: int
    duration: float
    error: str
    task_id: int | None


def empty_verification() -> VerificationResult:
    return {"performed": False, "passed": False, "details": []}


def empty_result(route: str = "", task_id: int | None = None) -> ExecutionResult:
    return {
        "status": "failed",
        "route": route,
        "display": "",
        "summary": "",
        "output_files": [],
        "actions": [],
        "steps": 0,
        "verification": empty_verification(),
        "tokens": 0,
        "duration": 0.0,
        "error": "",
        "task_id": task_id,
    }


def default_safety_policy(task_type: str) -> SafetyPolicy:
    """Return the default write policy for a task type."""
    if task_type == "modify":
        return {
            "auto_backup": True,
            "git_auto_save": False,
            "require_confirm": True,
            "diff_preview": True,
        }
    if task_type == "generate":
        return {
            "auto_backup": True,
            "git_auto_save": False,
            "require_confirm": True,
            "diff_preview": False,
        }
    return {
        "auto_backup": True,
        "git_auto_save": False,
        "require_confirm": False,
        "diff_preview": False,
    }


TASK_TYPE_MAP: dict[str, TaskType] = {
    "modify_config": "modify",
    "modify_code": "modify",
    "review_code": "review",
    "analyze_perf": "analyze",
    "analyze_deps": "analyze",
    "generate_test": "generate",
    "generate_system": "generate",
    "generate_shader": "generate",
    "generate_ui": "generate",
    "generate_editor_tool": "generate",
    "translate": "translate",
    "summarize_requirement": "analyze",
}


def infer_task_type(skill_id: str) -> TaskType:
    return TASK_TYPE_MAP.get(skill_id, "analyze")


VALIDATOR_MAP: dict[str, str] = {
    "modify_config": "ConfigModifyPlan",
    "modify_code": "CodeModifyPlan",
    "review_code": "CodeReviewOutput",
}


def infer_validator(skill_id: str) -> str | None:
    return VALIDATOR_MAP.get(skill_id)
