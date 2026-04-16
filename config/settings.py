import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "8192"))
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "120"))

    MAX_RETRIES: int = 3
    RETRY_BASE_DELAY: float = 1.0
    RETRY_MULTIPLIER: float = 2.0

    MAX_AGENT_STEPS: int = 20
    MAX_HANDOFFS_PER_TASK: int = int(os.getenv("MAX_HANDOFFS_PER_TASK", "8"))
    ENABLE_ORCHESTRATOR: bool = os.getenv("ENABLE_ORCHESTRATOR", "1").lower() in ("1", "true", "yes")

    DB_PATH: str = os.getenv("DB_PATH", "gamedev.db")
    LOG_DIR: str = "logs"
    OUTPUT_DIR: str = "output"
    SKILLS_DIR: str = "context/skills"
    SCHEMAS_DIR: str = "context/project_schemas"

    UNITY_EXECUTABLE_PATH: str = os.getenv("UNITY_EXECUTABLE_PATH", "")
    UNITY_BUILD_TIMEOUT: int = int(os.getenv("UNITY_BUILD_TIMEOUT", "300"))
    UNITY_TEST_WAIT_TIMEOUT: int = int(os.getenv("UNITY_TEST_WAIT_TIMEOUT", "120"))
    MCP_TOOL_TIMEOUT_MS: str = os.getenv("MCP_TOOL_TIMEOUT_MS", "720000")

    DEFAULT_VERIFY_MODE: str = os.getenv("DEFAULT_VERIFY_MODE", "syntax")
    # off    = 不验证（旧行为）
    # syntax = 仅语法层（永远可用，2-3 秒）
    # full   = 语法 + 真编译 + 真测试（需要 Unity，30-70 秒）

    LANGCHAIN_TRACING: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def get_model_providers(cls) -> dict:
        return {
            "deepseek": {
                "api_key_env": "DEEPSEEK_API_KEY",
                "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
                "client": "openai",
                "models": {
                    "chat": os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat"),
                    "reasoner": os.getenv("DEEPSEEK_REASONER_MODEL", "deepseek-reasoner"),
                },
            },
            "anthropic": {
                "api_key_env": "ANTHROPIC_API_KEY",
                "base_url": os.getenv("ANTHROPIC_BASE_URL", ""),
                "client": "anthropic",
                "models": {
                    "haiku": os.getenv("ANTHROPIC_HAIKU_MODEL", "claude-haiku-4-5"),
                    "sonnet": os.getenv("ANTHROPIC_SONNET_MODEL", "claude-sonnet-4-5"),
                },
            },
            "openai": {
                "api_key_env": "OPENAI_API_KEY",
                "base_url": os.getenv("OPENAI_BASE_URL", ""),
                "client": "openai",
                "models": {
                    "mini": os.getenv("OPENAI_MINI_MODEL", "gpt-5.4-mini"),
                    "full": os.getenv("OPENAI_FULL_MODEL", "gpt-5.4"),
                },
            },
        }

    @classmethod
    def get_task_model_map(cls) -> dict[str, tuple[str, str]]:
        return {
            "intent_parse": ("deepseek", "chat"),
            "routing": ("deepseek", "chat"),
            "review": ("deepseek", "chat"),
            "translate": ("deepseek", "chat"),
            "generation": ("anthropic", "haiku"),
            "fix_loop": ("anthropic", "haiku"),
            "plan": ("anthropic", "sonnet"),
            "requirement": ("anthropic", "sonnet"),
            "planning": ("anthropic", "sonnet"),
            "supervisor": ("deepseek", "chat"),
        }

    @classmethod
    def get_fallback_chain(cls) -> dict[str, tuple[str, str] | None]:
        return {
            "anthropic": ("openai", "mini"),
            "openai": ("deepseek", "chat"),
            "deepseek": None,
        }

    @classmethod
    def is_model_tiering_enabled(cls) -> bool:
        return os.getenv("ENABLE_MODEL_TIERING", "1").lower() in ("1", "true", "yes")

    @classmethod
    def is_unity_available(cls) -> bool:
        if not cls.UNITY_EXECUTABLE_PATH:
            return False
        return os.path.isfile(cls.UNITY_EXECUTABLE_PATH)
