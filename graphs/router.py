from __future__ import annotations

from typing import Any

from config.logger import get_logger
from graphs.base import AppServices
from prompts import router as router_prompt
from schemas.outputs import RouterDecision

logger = get_logger(__name__)


ROUTE_RULES: list[tuple[list[str], RouterDecision]] = [
    (
        ["审查", "review"],
        RouterDecision(
            intent="code_review",
            confidence=0.92,
            matched_pattern="review_code",
            target_pipeline="code_review",
            rationale="Matched code review keywords.",
        ),
    ),
    (
        ["测试", "nunit"],
        RouterDecision(
            intent="test_generate",
            confidence=0.88,
            matched_pattern="generate_system",
            target_pipeline="test_generate",
            rationale="Matched test generation keywords.",
        ),
    ),
    (
        ["shader", "着色"],
        RouterDecision(
            intent="shader_generate",
            confidence=0.9,
            matched_pattern="generate_content",
            target_pipeline="shader_generate",
            rationale="Matched shader keywords.",
        ),
    ),
    (
        ["性能", "优化", "audit"],
        RouterDecision(
            intent="performance_audit",
            confidence=0.86,
            matched_pattern="analyze_project",
            target_pipeline="performance_audit",
            rationale="Matched performance keywords.",
        ),
    ),
    (
        ["关卡", "level"],
        RouterDecision(
            intent="level_design",
            confidence=0.84,
            matched_pattern="generate_content",
            target_pipeline="level_design",
            rationale="Matched level design keywords.",
        ),
    ),
    (
        ["对话", "剧情", "dialogue"],
        RouterDecision(
            intent="dialogue_generate",
            confidence=0.86,
            matched_pattern="generate_content",
            target_pipeline="dialogue_generate",
            rationale="Matched dialogue keywords.",
        ),
    ),
    (
        ["翻译", "本地化", "localization"],
        RouterDecision(
            intent="localization",
            confidence=0.87,
            matched_pattern="translate_content",
            target_pipeline="localization",
            rationale="Matched localization keywords.",
        ),
    ),
    (
        ["依赖", "引用", "resource"],
        RouterDecision(
            intent="dependency_analysis",
            confidence=0.87,
            matched_pattern="analyze_project",
            target_pipeline="dependency_analysis",
            rationale="Matched dependency keywords.",
        ),
    ),
    (
        ["美术", "图标", "asset", "立绘"],
        RouterDecision(
            intent="asset_generate",
            confidence=0.83,
            matched_pattern="generate_content",
            target_pipeline="asset_generate",
            rationale="Matched art generation keywords.",
        ),
    ),
    (
        ["需求", "系统", "workflow", "做一个", "加一个"],
        RouterDecision(
            intent="requirement_workflow",
            confidence=0.8,
            matched_pattern="generate_system",
            target_pipeline="requirement_workflow",
            rationale="Matched complex requirement keywords.",
        ),
    ),
    (
        ["配置", "json", "数值"],
        RouterDecision(
            intent="config_generate",
            confidence=0.76,
            matched_pattern="generate_content",
            target_pipeline="config_generate",
            rationale="Matched config-related keywords.",
        ),
    ),
]


def route_input(user_input: str, services: AppServices | None = None) -> RouterDecision:
    lowered = user_input.lower()
    for keywords, decision in ROUTE_RULES:
        if any(keyword.lower() in lowered for keyword in keywords):
            return decision

    if services is not None:
        try:
            response = services.llm.invoke_structured(
                prompt=router_prompt.build_prompt(user_input, []),
                schema=RouterDecision,
                system_prompt=router_prompt.SYSTEM_PROMPT,
                task_type="router",
            )
            return response
        except Exception as exc:
            logger.warning("LLM router fallback failed: %s", exc)

    return RouterDecision(
        intent="code_generate",
        confidence=0.55,
        matched_pattern="generate_system",
        target_pipeline="code_generate",
        rationale="Defaulted to code generation.",
    )


def route_to_state_payload(user_input: str, services: AppServices | None = None) -> dict[str, Any]:
    decision = route_input(user_input, services)
    return decision.model_dump()
