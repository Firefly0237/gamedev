from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    llm_router_model: str = os.getenv("LLM_ROUTER_MODEL", "deepseek-chat")
    llm_generation_model: str = os.getenv("LLM_GENERATION_MODEL", "deepseek-chat")
    llm_review_model: str = os.getenv("LLM_REVIEW_MODEL", "deepseek-chat")
    llm_supervisor_model: str = os.getenv("LLM_SUPERVISOR_MODEL", "deepseek-chat")
    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "")
    langchain_tracing_v2: bool = _get_bool("LANGCHAIN_TRACING_V2", False)
    langchain_api_key: str = os.getenv("LANGCHAIN_API_KEY", "")
    langchain_project: str = os.getenv("LANGCHAIN_PROJECT", "GameDev")
    unity_project_path: str = os.getenv("UNITY_PROJECT_PATH", "")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    base_dir: Path = BASE_DIR
    logs_dir: Path = field(default_factory=lambda: BASE_DIR / "logs")
    output_dir: Path = field(default_factory=lambda: BASE_DIR / "output")
    db_path: Path = field(default_factory=lambda: BASE_DIR / "gamedev.db")
    checkpoint_db_path: Path = field(default_factory=lambda: BASE_DIR / "checkpoint.db")

    def ensure_directories(self) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings


settings = get_settings()
