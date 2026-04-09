from langchain_openai import ChatOpenAI

from config.logger import logger
from config.settings import Settings


def create_llm(
    task_type: str = "generation",
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
) -> ChatOpenAI:
    if not Settings.DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY 未配置")

    actual_model = model or Settings.get_model(task_type)
    actual_temperature = Settings.LLM_TEMPERATURE if temperature is None else temperature
    actual_max_tokens = Settings.LLM_MAX_TOKENS if max_tokens is None else max_tokens

    llm = ChatOpenAI(
        model=actual_model,
        api_key=Settings.DEEPSEEK_API_KEY,
        base_url=Settings.DEEPSEEK_BASE_URL,
        temperature=actual_temperature,
        max_completion_tokens=actual_max_tokens,
        timeout=Settings.LLM_TIMEOUT,
        max_retries=Settings.MAX_RETRIES,
        stream_usage=True,
    )
    logger.debug(f"LLM created: {task_type} -> {actual_model}")
    return llm
