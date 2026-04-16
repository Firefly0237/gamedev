from __future__ import annotations

import os
from dataclasses import dataclass, replace

from langchain_openai import ChatOpenAI

from config.logger import logger
from config.settings import Settings


@dataclass(frozen=True)
class LLMRuntimeInfo:
    task_type: str
    provider: str
    model: str
    model_key: str
    api_key: str
    api_key_env: str
    client: str
    base_url: str | None = None
    fallback_from: tuple[str, ...] = ()
    tiering_enabled: bool = True


_TASK_TYPE_ALIASES = {
    "planning": "plan",
    "supervisor": "routing",
}
_LAST_ROUTE_LOG: tuple[str, str, str] | None = None
_EMITTED_FALLBACK_WARNINGS: set[tuple[str, str, str]] = set()


def _normalize_task_type(task_type: str) -> str:
    return _TASK_TYPE_ALIASES.get(task_type, task_type)


def _normalize_base_url(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def _force_deepseek(task_type: str) -> LLMRuntimeInfo:
    providers = Settings.get_model_providers()
    cfg = providers["deepseek"]
    api_key = os.getenv(cfg["api_key_env"], "")
    if not api_key:
        raise RuntimeError("ENABLE_MODEL_TIERING=0 但未设置 DEEPSEEK_API_KEY")
    return LLMRuntimeInfo(
        task_type=task_type,
        provider="deepseek",
        model=cfg["models"]["chat"],
        model_key="chat",
        api_key=api_key,
        api_key_env=cfg["api_key_env"],
        client=cfg["client"],
        base_url=_normalize_base_url(cfg.get("base_url")),
        tiering_enabled=False,
    )


def resolve_task_model(task_type: str = "review") -> LLMRuntimeInfo:
    normalized_task = _normalize_task_type(task_type)
    if not Settings.is_model_tiering_enabled():
        return _force_deepseek(normalized_task)

    providers = Settings.get_model_providers()
    task_map = Settings.get_task_model_map()
    fallback_chain = Settings.get_fallback_chain()
    provider, model_key = task_map.get(normalized_task, ("deepseek", "chat"))
    visited: list[str] = []

    while provider:
        if provider in visited:
            raise RuntimeError(f"降级链成环: {' -> '.join(visited + [provider])}")
        visited.append(provider)

        cfg = providers[provider]
        api_key_env = cfg["api_key_env"]
        api_key = os.getenv(api_key_env, "")
        if api_key:
            return LLMRuntimeInfo(
                task_type=normalized_task,
                provider=provider,
                model=cfg["models"][model_key],
                model_key=model_key,
                api_key=api_key,
                api_key_env=api_key_env,
                client=cfg["client"],
                base_url=_normalize_base_url(cfg.get("base_url")),
                fallback_from=tuple(visited[:-1]),
                tiering_enabled=True,
            )

        fb = fallback_chain.get(provider)
        if not fb:
            raise RuntimeError(
                f"No LLM provider available for task={normalized_task}. "
                f"Tried: {visited}. 请至少配置一个 API_KEY。"
            )

        warn_key = (provider, api_key_env, fb[0], fb[1])
        if warn_key not in _EMITTED_FALLBACK_WARNINGS:
            logger.warning(f"[llm] {provider} 不可用（缺少 {api_key_env}），降级 -> {fb[0]}/{fb[1]}")
            _EMITTED_FALLBACK_WARNINGS.add(warn_key)
        provider, model_key = fb

    raise RuntimeError(f"未能解析 task={normalized_task} 的模型")


def get_llm_runtime_info(llm) -> LLMRuntimeInfo | None:
    return getattr(llm, "_gamedev_runtime_info", None)


def _log_route(info: LLMRuntimeInfo):
    global _LAST_ROUTE_LOG
    signature = (info.task_type, info.provider, info.model)
    if signature == _LAST_ROUTE_LOG:
        return
    logger.info(f"[llm] task={info.task_type} -> {info.provider}/{info.model}")
    _LAST_ROUTE_LOG = signature


def create_llm(
    task_type: str = "generation",
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
):
    resolved = resolve_task_model(task_type)
    actual_model = model or resolved.model
    info = replace(resolved, model=actual_model)
    actual_temperature = Settings.LLM_TEMPERATURE if temperature is None else temperature
    actual_max_tokens = Settings.LLM_MAX_TOKENS if max_tokens is None else max_tokens

    if info.client == "anthropic":
        from langchain_anthropic import ChatAnthropic

        kwargs = {
            "model": actual_model,
            "anthropic_api_key": info.api_key,
            "temperature": actual_temperature,
            "max_tokens": actual_max_tokens,
            "timeout": Settings.LLM_TIMEOUT,
            "max_retries": Settings.MAX_RETRIES,
        }
        if info.base_url:
            kwargs["base_url"] = info.base_url

        llm = ChatAnthropic(
            **kwargs,
        )
    else:
        llm = ChatOpenAI(
            model=actual_model,
            api_key=info.api_key,
            base_url=info.base_url,
            temperature=actual_temperature,
            max_completion_tokens=actual_max_tokens,
            timeout=Settings.LLM_TIMEOUT,
            max_retries=Settings.MAX_RETRIES,
            stream_usage=True,
        )

    setattr(llm, "_gamedev_runtime_info", info)
    _log_route(info)
    return llm
