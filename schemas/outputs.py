import json
import re
from typing import Literal

from pydantic import BaseModel, Field


class ConfigModifyAction(BaseModel):
    """单条配置修改操作"""

    file_path: str
    match_field: str
    match_value: str | int
    target_field: str
    old_value: str | int | float
    new_value: str | int | float


class ConfigModifyPlan(BaseModel):
    """配置修改计划"""

    actions: list[ConfigModifyAction] = Field(min_length=1)
    summary: str


class ConfigBatchAction(BaseModel):
    """单条批量配置修改规则"""

    file_path: str
    filter: dict = Field(default_factory=dict)
    operation: Literal["multiply", "add", "set"]
    target_field: str
    value: float | int | str


class ConfigBatchPlan(BaseModel):
    """批量配置修改计划"""

    actions: list[ConfigBatchAction] = Field(min_length=1)
    summary: str


class CodeModifyAction(BaseModel):
    """单条代码修改操作"""

    file_path: str
    search_pattern: str = Field(min_length=3)
    replace_with: str


class CodeModifyPlan(BaseModel):
    """代码修改计划"""

    actions: list[CodeModifyAction] = Field(min_length=1)
    summary: str


class CodeIssue(BaseModel):
    """代码审查中的单个问题"""

    severity: Literal["critical", "warning", "suggestion"]
    line: int = Field(ge=0)
    category: Literal["performance", "convention", "antipattern", "safety"]
    description: str = Field(min_length=5)
    suggestion: str = Field(min_length=5)
    code_fix: str = ""


class CodeReviewOutput(BaseModel):
    """代码审查报告"""

    file_path: str
    summary: str
    issues: list[CodeIssue] = Field(default_factory=list)
    score: int = Field(ge=0, le=100)


class SubTask(BaseModel):
    """单个子任务"""

    step_id: int = Field(ge=1)
    description: str = Field(min_length=10, max_length=200)
    target_files: list[str] = Field(min_length=1, max_length=5)
    tool_hint: Literal["read", "write", "verify", "mixed"]
    depends_on: list[int] = Field(default_factory=list)


class SubTaskPlan(BaseModel):
    """Orchestrator 的执行计划"""

    subtasks: list[SubTask] = Field(min_length=1, max_length=8)
    summary: str = Field(min_length=5)


class WorkerAgentResult(BaseModel):
    """单个 Worker 的结构化执行结果。"""

    worker: str = Field(min_length=3)
    status: Literal["success", "failed"]
    summary: str = Field(min_length=2)
    created_files: list[str] = Field(default_factory=list, max_length=5)
    error_code: str = ""
    error_details: str = ""


def try_parse(text: str, model: type[BaseModel]) -> tuple[BaseModel | None, str]:
    """尝试从文本中解析 JSON 并校验，失败返回 (None, 错误信息)"""

    json_str = text

    match = re.search(r"```json\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        match = re.search(r"```\s*\n(.*?)\n\s*```", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                json_str = match.group(0)

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as exc:
        return None, f"JSON 解析失败: {exc}"

    try:
        result = model(**parsed)
        return result, ""
    except Exception as exc:
        error_msg = str(exc)[:300]
        return None, f"校验失败: {error_msg}"
