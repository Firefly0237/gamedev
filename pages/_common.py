from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import streamlit as st

from config.settings import get_project_root
from graphs import get_pipeline, run_pipeline
from graphs.base import create_services
from schemas.outputs import PipelineResult


@st.cache_resource
def get_services():
    return create_services()


def resolve_project_root() -> str:
    project_root = st.session_state.get("project_root")
    if project_root:
        return project_root
    project_root = str(get_project_root())
    st.session_state["project_root"] = project_root
    return project_root


def persist_project_root(project_root: str) -> str:
    st.session_state["project_root"] = project_root
    return project_root


def refresh_project_context(project_root: str) -> dict[str, Any]:
    services = get_services()
    root = Path(project_root).resolve()
    if not root.exists():
        return {"project_root": str(root), "summary": "Project root does not exist yet.", "metadata": {"missing": True}}
    context = services.scanner.scan_project(root).to_dict()
    services.scanner.generate_project_schemas(root, services.settings.project_schema_dir)
    services.db.save_project_context(str(root), context)
    return context


def get_cached_project_context(project_root: str) -> dict[str, Any] | None:
    services = get_services()
    return services.db.get_project_context(str(Path(project_root).resolve()))


def parse_json_input(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if not text:
        return {}
    return json.loads(text)


def render_pipeline_result(result: PipelineResult) -> None:
    st.subheader("结果")
    status_map = {
        "success": st.success,
        "warning": st.warning,
        "error": st.error,
    }
    status_map.get(result.status, st.info)(result.message)

    if result.steps:
        st.markdown("**执行链路**")
        for idx, step in enumerate(result.steps, start=1):
            st.write(f"{idx}. [{step.stage}] {step.detail}")

    if result.data:
        st.markdown("**输出数据**")
        st.json(result.data)

    if result.artifacts:
        st.markdown("**产物**")
        for artifact in result.artifacts:
            st.write(f"- {artifact.artifact_type}: {artifact.path}")
            if artifact.content_preview:
                st.code(artifact.content_preview)

    if result.warnings:
        st.markdown("**警告**")
        for warning in result.warnings:
            st.warning(warning)

    if result.errors:
        st.markdown("**错误**")
        for error in result.errors:
            st.error(error)


def render_pipeline_page(
    pipeline_key: str,
    title: str,
    description: str,
    params_example: dict[str, Any] | None = None,
) -> None:
    definition = get_pipeline(pipeline_key)
    st.title(title)
    st.caption(description)

    current_root = resolve_project_root()
    project_root = st.text_input("项目路径", value=current_root, key=f"{pipeline_key}_project_root")
    persist_project_root(project_root)

    with st.form(f"{pipeline_key}_form"):
        user_input = st.text_area(definition.input_label, placeholder=definition.placeholder, height=160)
        params_text = st.text_area(
            "额外参数（JSON，可选）",
            value=json.dumps(params_example or {}, ensure_ascii=False, indent=2),
            height=180,
        )
        submitted = st.form_submit_button("执行")

    if submitted:
        try:
            params = parse_json_input(params_text)
            result = run_pipeline(
                pipeline_name=pipeline_key,
                user_input=user_input or definition.placeholder,
                project_root=project_root,
                params=params,
                services=get_services(),
            )
            st.session_state[f"result_{pipeline_key}"] = result.model_dump()
        except json.JSONDecodeError as exc:
            st.error(f"JSON 参数格式错误: {exc}")

    cached = st.session_state.get(f"result_{pipeline_key}")
    if cached:
        render_pipeline_result(PipelineResult.model_validate(cached))


def run_git(project_root: str, args: list[str]) -> str:
    root = Path(project_root)
    if not (root / ".git").exists():
        return "No git repository found."
    try:
        completed = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
        return completed.stdout.strip() or completed.stderr.strip() or "OK"
    except subprocess.CalledProcessError as exc:
        return exc.stderr.strip() or exc.stdout.strip() or str(exc)
