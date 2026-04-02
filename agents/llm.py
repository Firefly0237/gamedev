from __future__ import annotations

from langchain_openai import ChatOpenAI

from config.logger import logger
from config.settings import Settings


def create_llm(
    task_type: str = "generation",
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> ChatOpenAI:
    """Create a ChatOpenAI client for the requested task type.

    Usage:
        llm = create_llm(task_type="generation")
        llm = create_llm(task_type="router")
        llm = create_llm(model="deepseek-reasoner", temperature=0.1)
    """
    if not Settings.DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY 未配置，请在 .env 或界面侧边栏中设置。")

    selected_model = model
    base_url = Settings.DEEPSEEK_BASE_URL
    if not selected_model:
        selected_model, base_url = Settings.get_model(task_type)

    logger.debug(
        "创建 LLM 实例 | task_type=%s | model=%s | base_url=%s",
        task_type,
        selected_model,
        base_url,
    )

    return ChatOpenAI(
        model=selected_model,
        api_key=Settings.DEEPSEEK_API_KEY,
        base_url=base_url,
        temperature=temperature if temperature is not None else Settings.LLM_TEMPERATURE,
        max_tokens=max_tokens if max_tokens is not None else Settings.LLM_MAX_TOKENS,
        timeout=Settings.LLM_TIMEOUT,
    )
