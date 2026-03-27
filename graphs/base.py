from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from typing_extensions import TypedDict

from agents.llm import LLMClient
from config.logger import configure_logging, get_logger
from config.settings import AppSettings, get_settings
from context.loader import ContextLoader
from database.checkpoint import create_checkpointer
from database.db import DatabaseManager, TaskLogRecord
from mcp_tools.mcp_client import MCPClientManager
from scanner.unity_scanner import UnityScanner
from schemas.outputs import ExecutionStep, GeneratedArtifact, PipelineResult

logger = get_logger(__name__)


class PipelineState(TypedDict, total=False):
    user_input: str
    project_root: str
    intent: str
    matched_pattern: str | None
    target_pipeline: str
    target_hint: str
    params: dict[str, Any]
    context: dict[str, Any]
    output: dict[str, Any]
    execution_trace: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]
    warnings: list[str]
    errors: list[str]
    retry_count: int
    journal: list[dict[str, Any]]


PipelineHandler = Callable[[PipelineState, "AppServices"], PipelineResult]


@dataclass(slots=True)
class PipelineDefinition:
    key: str
    title: str
    category: str
    mode: str
    description: str
    pattern: str | None
    input_label: str
    placeholder: str
    handler: PipelineHandler
    visible_in_ui: bool = True


@dataclass(slots=True)
class AppServices:
    settings: AppSettings
    db: DatabaseManager
    checkpointer: Any | None
    scanner: UnityScanner
    llm: LLMClient
    context_loader: ContextLoader
    mcp: MCPClientManager


PIPELINE_REGISTRY: dict[str, PipelineDefinition] = {}


def register_pipeline(definition: PipelineDefinition) -> PipelineDefinition:
    PIPELINE_REGISTRY[definition.key] = definition
    return definition


def get_pipeline(key: str) -> PipelineDefinition:
    return PIPELINE_REGISTRY[key]


def list_pipelines(visible_only: bool = True) -> list[PipelineDefinition]:
    pipelines = list(PIPELINE_REGISTRY.values())
    if visible_only:
        pipelines = [item for item in pipelines if item.visible_in_ui]
    return sorted(pipelines, key=lambda item: (item.category, item.title))


def create_services() -> AppServices:
    configure_logging()
    settings = get_settings()
    db = DatabaseManager(settings.database_file)
    mcp = MCPClientManager()
    mcp.load_default_placeholders()
    return AppServices(
        settings=settings,
        db=db,
        checkpointer=create_checkpointer(settings.checkpoint_file),
        scanner=UnityScanner(),
        llm=LLMClient(),
        context_loader=ContextLoader(),
        mcp=mcp,
    )


def create_initial_state(
    pipeline_name: str,
    user_input: str,
    project_root: str,
    params: dict[str, Any] | None = None,
    matched_pattern: str | None = None,
    intent: str | None = None,
) -> PipelineState:
    return PipelineState(
        user_input=user_input,
        project_root=project_root,
        target_pipeline=pipeline_name,
        matched_pattern=matched_pattern,
        intent=intent or pipeline_name,
        target_hint="",
        params=params or {},
        context={},
        output={},
        execution_trace=[],
        artifacts=[],
        warnings=[],
        errors=[],
        retry_count=0,
        journal=[],
    )


def record_step(
    state: PipelineState,
    stage: str,
    detail: str,
    status: str = "completed",
    payload: dict[str, Any] | None = None,
) -> None:
    item = ExecutionStep(stage=stage, detail=detail, status=status, payload=payload or {})
    state.setdefault("execution_trace", []).append(item.model_dump())


def add_artifact(
    state: PipelineState,
    path: str,
    artifact_type: str,
    summary: str,
    content_preview: str = "",
) -> None:
    artifact = GeneratedArtifact(
        path=path,
        artifact_type=artifact_type,
        summary=summary,
        content_preview=content_preview,
    )
    state.setdefault("artifacts", []).append(artifact.model_dump())


def ensure_project_context(state: PipelineState, services: AppServices) -> dict[str, Any]:
    project_root = Path(state["project_root"]).resolve()
    cached = services.db.get_project_context(str(project_root))
    if cached:
        state["context"] = services.context_loader.build_context_layers(
            project_context=cached,
            pattern_name=state.get("matched_pattern"),
            target_hint=state.get("target_hint", ""),
        )
        record_step(state, "context", "Loaded cached project context.")
        return cached

    if not project_root.exists():
        placeholder = {
            "project_root": str(project_root),
            "engine": "unity",
            "summary": "Project root does not exist yet.",
            "directory_tree": [],
            "scripts": [],
            "scenes": [],
            "config_files": [],
            "metadata": {"missing": True},
        }
        state["context"] = services.context_loader.build_context_layers(
            project_context=placeholder,
            pattern_name=state.get("matched_pattern"),
            target_hint=state.get("target_hint", ""),
        )
        record_step(state, "context", "Project root is missing; using placeholder context.", status="failed")
        return placeholder

    project_context = services.scanner.scan_project(project_root).to_dict()
    generated_schemas = services.scanner.generate_project_schemas(project_root, services.settings.project_schema_dir)
    if generated_schemas:
        project_context.setdefault("metadata", {})["generated_schema_count"] = len(generated_schemas)
    services.db.save_project_context(str(project_root), project_context)
    state["context"] = services.context_loader.build_context_layers(
        project_context=project_context,
        pattern_name=state.get("matched_pattern"),
        target_hint=state.get("target_hint", ""),
    )
    record_step(state, "context", "Scanned project and refreshed project schema cache.")
    return project_context


def finalize_result(
    pipeline_name: str,
    state: PipelineState,
    status: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> PipelineResult:
    return PipelineResult(
        pipeline_name=pipeline_name,
        status=status,
        message=message,
        steps=state.get("execution_trace", []),
        artifacts=state.get("artifacts", []),
        data=data or state.get("output", {}),
        warnings=state.get("warnings", []),
        errors=state.get("errors", []),
    )


def build_placeholder_result(
    state: PipelineState,
    pipeline_name: str,
    headline: str,
    next_steps: list[str],
    extra_data: dict[str, Any] | None = None,
) -> PipelineResult:
    ensure_project_context(state, services=create_services())
    record_step(state, "pipeline", headline)
    state["output"] = {
        "next_steps": next_steps,
        "context_summary": state.get("context", {}).get("project_overview", {}).get("summary", ""),
    }
    if extra_data:
        state["output"].update(extra_data)
    return finalize_result(
        pipeline_name=pipeline_name,
        state=state,
        status="success",
        message=headline,
    )


def run_pipeline(
    pipeline_name: str,
    user_input: str,
    project_root: str,
    params: dict[str, Any] | None = None,
    matched_pattern: str | None = None,
    intent: str | None = None,
    services: AppServices | None = None,
) -> PipelineResult:
    services = services or create_services()
    definition = get_pipeline(pipeline_name)
    state = create_initial_state(
        pipeline_name=pipeline_name,
        user_input=user_input,
        project_root=project_root,
        params=params,
        matched_pattern=matched_pattern or definition.pattern,
        intent=intent,
    )
    record_step(state, "start", f"Running pipeline {pipeline_name}.", status="running")
    try:
        result = definition.handler(state, services)
    except Exception as exc:  # pragma: no cover - defensive boundary
        logger.exception("Pipeline %s failed", pipeline_name)
        state.setdefault("errors", []).append(str(exc))
        record_step(state, "pipeline", f"{pipeline_name} failed: {exc}", status="failed")
        result = finalize_result(
            pipeline_name=pipeline_name,
            state=state,
            status="error",
            message=f"{pipeline_name} failed.",
        )
    services.db.log_task(
        TaskLogRecord(
            task_type=pipeline_name,
            status=result.status,
            input_payload={"user_input": user_input, "params": params or {}, "project_root": project_root},
            output_payload=result.model_dump(),
            execution_trace=result.model_dump()["steps"],
        )
    )
    return result
