from dataclasses import dataclass, field
from abc import ABC, abstractmethod

@dataclass
class ProjectContext:
    """项目上下文（引擎无关的通用字段）"""
    project_path: str
    engine: str = ""                              # "unity" / "unreal" / "godot"
    engine_version: str = ""
    scripts: list[dict] = field(default_factory=list)
    scenes: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    localization_files: list[str] = field(default_factory=list)
    shader_files: list[str] = field(default_factory=list)
    prefabs: list[str] = field(default_factory=list)
    directory_tree: str = ""
    total_scripts: int = 0

class BaseScanner(ABC):
    """扫描器抽象基类，定义所有引擎 Scanner 必须实现的接口"""

    def __init__(self, project_path: str):
        self.project_path = project_path

    @abstractmethod
    def validate_project(self) -> tuple[bool, str]:
        """验证路径是否是有效的游戏项目"""
        ...

    @abstractmethod
    def scan(self) -> ProjectContext:
        """执行完整项目扫描"""
        ...

    @abstractmethod
    def get_script_list(self) -> list[str]:
        """获取所有代码文件路径"""
        ...
