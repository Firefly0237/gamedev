from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


class Settings:
    PROJECT_ROOT = PROJECT_ROOT

    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").strip()
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "").strip()

    _DEFAULT_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
    LLM_ROUTER_MODEL = os.getenv("LLM_ROUTER_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL
    LLM_GENERATION_MODEL = os.getenv("LLM_GENERATION_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL
    LLM_REVIEW_MODEL = os.getenv("LLM_REVIEW_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL
    LLM_SUPERVISOR_MODEL = os.getenv("LLM_SUPERVISOR_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL

    LLM_TEMPERATURE = _get_float("LLM_TEMPERATURE", 0.3)
    LLM_MAX_TOKENS = _get_int("LLM_MAX_TOKENS", 4096)
    LLM_TIMEOUT = _get_int("LLM_TIMEOUT", 120)

    MAX_RETRIES = _get_int("MAX_RETRIES", 3)
    RETRY_BASE_DELAY = _get_float("RETRY_BASE_DELAY", 1.0)
    RETRY_MULTIPLIER = _get_float("RETRY_MULTIPLIER", 2.0)

    UNITY_PROJECT_PATH = os.getenv("UNITY_PROJECT_PATH", "").strip()
    DB_PATH = PROJECT_ROOT / "gamedev.db"
    LOG_DIR = PROJECT_ROOT / "logs"
    OUTPUT_DIR = PROJECT_ROOT / "output"

    UNITY_EDITOR_PATH = os.getenv("UNITY_EDITOR_PATH", "").strip()
    ENABLE_UNITY_COMPILE = _get_bool("ENABLE_UNITY_COMPILE", False)

    LANGCHAIN_TRACING = _get_bool(
        "LANGCHAIN_TRACING",
        _get_bool("LANGCHAIN_TRACING_V2", False),
    )
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "").strip()
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "GameDev").strip() or "GameDev"

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"

    ENGINE_TOOL_MAP = {
        "unity": {
            "filesystem": "@modelcontextprotocol/server-filesystem",
            "git": "mcp-server-git",
        },
        "unreal": {},
        "godot": {},
    }

    @classmethod
    def ensure_dirs(cls) -> None:
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls) -> list[str]:
        warnings: list[str] = []

        if cls.DEEPSEEK_API_KEY:
            warnings.append("✅ DEEPSEEK_API_KEY 已配置")
        else:
            warnings.append("❌ DEEPSEEK_API_KEY 未配置")

        if cls.DASHSCOPE_API_KEY:
            warnings.append("✅ DASHSCOPE_API_KEY 已配置")
        else:
            warnings.append("⚠️ DASHSCOPE_API_KEY 未配置（美术资产生成功能将不可用）")

        if cls.LANGCHAIN_API_KEY:
            warnings.append("✅ LANGCHAIN_API_KEY 已配置")
        else:
            warnings.append("⚠️ LANGCHAIN_API_KEY 未配置（LangSmith 可视化将不可用）")

        return warnings

    @classmethod
    def update_api_key(cls, key: str) -> None:
        clean_key = key.strip()
        cls.DEEPSEEK_API_KEY = clean_key
        os.environ["DEEPSEEK_API_KEY"] = clean_key

    @classmethod
    def get_model(cls, task_type: str) -> tuple[str, str]:
        model_map = {
            "router": cls.LLM_ROUTER_MODEL,
            "generation": cls.LLM_GENERATION_MODEL,
            "review": cls.LLM_REVIEW_MODEL,
            "supervisor": cls.LLM_SUPERVISOR_MODEL,
        }
        if task_type not in model_map:
            raise ValueError(f"Unsupported task_type: {task_type}")
        return model_map[task_type], cls.DEEPSEEK_BASE_URL


class _SettingsCompat:
    @property
    def deepseek_api_key(self) -> str:
        return Settings.DEEPSEEK_API_KEY

    @property
    def deepseek_base_url(self) -> str:
        return Settings.DEEPSEEK_BASE_URL

    @property
    def deepseek_model(self) -> str:
        return Settings.LLM_GENERATION_MODEL

    @property
    def llm_router_model(self) -> str:
        return Settings.LLM_ROUTER_MODEL

    @property
    def llm_generation_model(self) -> str:
        return Settings.LLM_GENERATION_MODEL

    @property
    def llm_review_model(self) -> str:
        return Settings.LLM_REVIEW_MODEL

    @property
    def llm_supervisor_model(self) -> str:
        return Settings.LLM_SUPERVISOR_MODEL

    @property
    def dashscope_api_key(self) -> str:
        return Settings.DASHSCOPE_API_KEY

    @property
    def langchain_tracing_v2(self) -> bool:
        return Settings.LANGCHAIN_TRACING

    @property
    def langchain_api_key(self) -> str:
        return Settings.LANGCHAIN_API_KEY

    @property
    def langchain_project(self) -> str:
        return Settings.LANGCHAIN_PROJECT

    @property
    def unity_project_path(self) -> str:
        return Settings.UNITY_PROJECT_PATH

    @property
    def log_level(self) -> str:
        return Settings.LOG_LEVEL

    @property
    def base_dir(self) -> Path:
        return Settings.PROJECT_ROOT

    @property
    def logs_dir(self) -> Path:
        return Settings.LOG_DIR

    @property
    def output_dir(self) -> Path:
        return Settings.OUTPUT_DIR

    @property
    def db_path(self) -> Path:
        return Settings.DB_PATH

    @property
    def checkpoint_db_path(self) -> Path:
        return Settings.DB_PATH

    def ensure_directories(self) -> None:
        Settings.ensure_dirs()


Settings.ensure_dirs()
settings = _SettingsCompat()
