from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ExecutionStep(BaseModel):
    stage: str
    status: Literal["pending", "running", "completed", "failed"] = "completed"
    detail: str
    payload: dict[str, Any] = Field(default_factory=dict)


class RouterDecision(BaseModel):
    intent: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    matched_pattern: str | None = None
    target_pipeline: str
    rationale: str = ""


class ConfigEditInstruction(BaseModel):
    file_path: str
    record_locator_field: str
    record_locator_value: str
    target_field: str
    old_value: Any | None = None
    new_value: Any


class CodeEditInstruction(BaseModel):
    file_path: str
    search_text: str
    replace_text: str
    old_value: str | None = None


class GeneratedArtifact(BaseModel):
    path: str
    artifact_type: str
    summary: str
    content_preview: str = ""


class ReviewFinding(BaseModel):
    severity: Literal["low", "medium", "high"] = "medium"
    title: str
    description: str
    file_path: str | None = None
    line: int | None = None
    recommendation: str = ""


class PipelineResult(BaseModel):
    pipeline_name: str
    status: Literal["success", "warning", "error"] = "success"
    message: str
    steps: list[ExecutionStep] = Field(default_factory=list)
    artifacts: list[GeneratedArtifact] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class SupervisorTask(BaseModel):
    task_id: str
    title: str
    pipeline_name: str
    depends_on: list[str] = Field(default_factory=list)
    description: str
    status: Literal["pending", "running", "completed", "blocked"] = "pending"


class SupervisorPlan(BaseModel):
    requirement: str
    tasks: list[SupervisorTask] = Field(default_factory=list)
    evaluation_notes: list[str] = Field(default_factory=list)


class ProjectSchemaInfo(BaseModel):
    schema_name: str
    file_path: str
    locator_field: str | None = None
    fields: list[str] = Field(default_factory=list)
    sample_record: dict[str, Any] = Field(default_factory=dict)
