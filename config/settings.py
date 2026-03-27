from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseModel):
    provider: str = "mock"
    base_url: str | None = None
    api_key: str | None = None
    router_model: str = "deepseek-chat"
    generation_model: str = "deepseek-chat"
    review_model: str = "deepseek-chat"
    supervisor_model: str = "deepseek-reasoner"


class MCPServerConfig(BaseModel):
    name: str
    command: str
    args: list[str] = Field(default_factory=list)
    enabled: bool = True
    server_type: str = "generic"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "GameDev"
    debug: bool = True
    default_project_root: str = ""
    database_path: str = "database/gamedev.db"
    checkpoint_db_path: str = "database/checkpoints.db"
    log_level: str = "INFO"
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "gamedev"

    llm_provider: str = "mock"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_router_model: str = "deepseek-chat"
    llm_generation_model: str = "deepseek-chat"
    llm_review_model: str = "deepseek-chat"
    llm_supervisor_model: str = "deepseek-reasoner"

    @property
    def root_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def database_file(self) -> Path:
        return (self.root_dir / self.database_path).resolve()

    @property
    def checkpoint_file(self) -> Path:
        return (self.root_dir / self.checkpoint_db_path).resolve()

    @property
    def logs_dir(self) -> Path:
        return (self.root_dir / "logs").resolve()

    @property
    def output_dir(self) -> Path:
        return (self.root_dir / "output").resolve()

    @property
    def patterns_dir(self) -> Path:
        return (self.root_dir / "context" / "patterns").resolve()

    @property
    def project_schema_dir(self) -> Path:
        return (self.root_dir / "context" / "project_schemas").resolve()

    @property
    def model(self) -> ModelConfig:
        return ModelConfig(
            provider=self.llm_provider,
            base_url=self.llm_base_url or None,
            api_key=self.llm_api_key or None,
            router_model=self.llm_router_model,
            generation_model=self.llm_generation_model,
            review_model=self.llm_review_model,
            supervisor_model=self.llm_supervisor_model,
        )

    @property
    def engine_tool_aliases(self) -> dict[str, dict[str, str]]:
        return {
            "unity": {
                "engine_compile": "unity_compile",
                "engine_execute": "unity_execute",
                "engine_scene": "unity_scene_hierarchy",
                "engine_screenshot": "unity_screenshot",
            },
            "generic": {
                "engine_compile": "engine_compile",
                "engine_execute": "engine_execute",
                "engine_scene": "engine_scene",
                "engine_screenshot": "engine_screenshot",
            },
        }

    @property
    def mcp_servers(self) -> list[MCPServerConfig]:
        return [
            MCPServerConfig(name="filesystem", command="npx", args=["-y", "@modelcontextprotocol/server-filesystem"], server_type="fs"),
            MCPServerConfig(name="git", command="npx", args=["-y", "@modelcontextprotocol/server-git"], server_type="git"),
            MCPServerConfig(name="unity", command="unity-mcp", args=[], enabled=False, server_type="unity"),
            MCPServerConfig(name="gamedev", command="python", args=["-m", "mcp_tools.mcp_server_gamedev"], server_type="gamedev"),
        ]


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    load_dotenv(override=False)
    settings = AppSettings()
    for path in (settings.database_file, settings.checkpoint_file):
        path.parent.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.project_schema_dir.mkdir(parents=True, exist_ok=True)
    return settings


def get_project_root() -> Path:
    settings = get_settings()
    configured = settings.default_project_root or os.getenv("DEFAULT_PROJECT_ROOT", "")
    if configured:
        return Path(configured).resolve()
    return settings.root_dir
