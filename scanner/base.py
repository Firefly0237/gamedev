from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ProjectContext:
    """项目上下文（引擎无关）"""

    project_path: str = ""
    engine: str = ""
    engine_version: str = ""
    detected_genre: str = "unknown"
    scripts: list = field(default_factory=list)
    scenes: list = field(default_factory=list)
    assets: list = field(default_factory=list)
    config_files: list = field(default_factory=list)
    localization_files: list = field(default_factory=list)
    shader_files: list = field(default_factory=list)
    prefabs: list = field(default_factory=list)
    directory_tree: str = ""
    total_scripts: int = 0


class BaseScanner(ABC):
    def __init__(self, project_path: str):
        self.project_path = project_path

    @abstractmethod
    def validate_project(self) -> tuple[bool, str]:
        raise NotImplementedError

    @abstractmethod
    def scan(self) -> ProjectContext:
        raise NotImplementedError

    @abstractmethod
    def get_script_list(self) -> list[str]:
        raise NotImplementedError

    def get_config_list(self) -> list[str]:
        return []

    def get_shader_list(self) -> list[str]:
        return []

    def get_localization_list(self) -> list[str]:
        return []
