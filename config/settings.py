import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    MODEL_MAP: dict = {
        "generation": os.getenv("LLM_GENERATION_MODEL", "deepseek-chat"),
        "review": os.getenv("LLM_REVIEW_MODEL", "deepseek-chat"),
        "supervisor": os.getenv("LLM_SUPERVISOR_MODEL", "deepseek-chat"),
    }

    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096
    LLM_TIMEOUT: int = 120

    MAX_RETRIES: int = 3
    RETRY_BASE_DELAY: float = 1.0
    RETRY_MULTIPLIER: float = 2.0

    MAX_AGENT_STEPS: int = 20

    DB_PATH: str = os.getenv("DB_PATH", "gamedev.db")
    LOG_DIR: str = "logs"
    OUTPUT_DIR: str = "output"
    SKILLS_DIR: str = "context/skills"
    SCHEMAS_DIR: str = "context/project_schemas"

    UNITY_EXECUTABLE_PATH: str = os.getenv("UNITY_EXECUTABLE_PATH", "")
    UNITY_BUILD_TIMEOUT: int = int(os.getenv("UNITY_BUILD_TIMEOUT", "300"))

    LANGCHAIN_TRACING: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def get_model(cls, task_type: str) -> str:
        return cls.MODEL_MAP.get(task_type, cls.DEEPSEEK_MODEL)

    @classmethod
    def is_unity_available(cls) -> bool:
        if not cls.UNITY_EXECUTABLE_PATH:
            return False
        return os.path.isfile(cls.UNITY_EXECUTABLE_PATH)
