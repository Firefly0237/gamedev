from __future__ import annotations

from pathlib import Path

from scanner.base import BaseScanner, ProjectContext


class UnityScanner(BaseScanner):
    """Unity 项目扫描器，负责提取脚本、场景、资源和配置等上下文信息。"""

    shader_extensions = {".shader", ".shadergraph", ".compute"}
    config_extensions = {".json", ".asset", ".yaml", ".yml"}
    localization_extensions = {".csv", ".tsv", ".json"}
    asset_extensions = {
        ".png",
        ".jpg",
        ".jpeg",
        ".tga",
        ".psd",
        ".fbx",
        ".mat",
        ".anim",
        ".controller",
        ".wav",
        ".mp3",
        ".ogg",
    }

    def validate_project(self) -> tuple[bool, str]:
        root = Path(self.project_path)
        if not root.exists():
            return False, "项目路径不存在。"
        if not root.is_dir():
            return False, "项目路径不是目录。"
        if not (root / "Assets").exists():
            return False, "缺少 Assets 目录。"
        if not (root / "ProjectSettings").exists():
            return False, "缺少 ProjectSettings 目录。"
        return True, "Unity 项目路径有效。"

    def scan(self) -> ProjectContext:
        valid, message = self.validate_project()
        if not valid:
            raise ValueError(message)

        root = Path(self.project_path).resolve()
        assets_dir = root / "Assets"

        scripts = self._collect_scripts(root)
        scenes = self._collect_relative_paths(assets_dir, "*.unity", root)
        shader_files = self._collect_by_extensions(assets_dir, self.shader_extensions, root)
        config_files = self._collect_config_files(root)
        localization_files = self._collect_localization_files(root)
        prefabs = self._collect_relative_paths(assets_dir, "*.prefab", root)
        assets = self._collect_asset_files(assets_dir, root)

        return ProjectContext(
            project_path=str(root),
            engine="unity",
            engine_version=self._read_engine_version(root / "ProjectSettings" / "ProjectVersion.txt"),
            scripts=scripts,
            scenes=scenes,
            assets=assets,
            config_files=config_files,
            localization_files=localization_files,
            shader_files=shader_files,
            prefabs=prefabs,
            directory_tree=self._build_directory_tree(root),
            total_scripts=len(scripts),
        )

    def get_script_list(self) -> list[str]:
        valid, _ = self.validate_project()
        if not valid:
            return []
        root = Path(self.project_path).resolve()
        return [item["path"] for item in self._collect_scripts(root)]

    def _collect_scripts(self, root: Path) -> list[dict]:
        script_files = []
        for file_path in sorted((root / "Assets").rglob("*.cs")):
            relative_path = file_path.relative_to(root).as_posix()
            script_files.append(
                {
                    "name": file_path.stem,
                    "path": relative_path,
                    "directory": file_path.parent.relative_to(root).as_posix(),
                    "extension": file_path.suffix,
                }
            )
        return script_files

    def _collect_relative_paths(self, base_dir: Path, pattern: str, root: Path) -> list[str]:
        return [path.relative_to(root).as_posix() for path in sorted(base_dir.rglob(pattern))]

    def _collect_by_extensions(self, base_dir: Path, extensions: set[str], root: Path) -> list[str]:
        matched = []
        for path in sorted(base_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in extensions:
                matched.append(path.relative_to(root).as_posix())
        return matched

    def _collect_config_files(self, root: Path) -> list[str]:
        matched = []
        for folder_name in ("Assets", "ProjectSettings"):
            base_dir = root / folder_name
            if not base_dir.exists():
                continue
            for path in sorted(base_dir.rglob("*")):
                if path.is_file() and path.suffix.lower() in self.config_extensions:
                    matched.append(path.relative_to(root).as_posix())
        return matched

    def _collect_localization_files(self, root: Path) -> list[str]:
        matched = []
        for path in sorted((root / "Assets").rglob("*")):
            if not path.is_file():
                continue
            lower_name = path.name.lower()
            if "localization" in lower_name or "locale" in lower_name:
                matched.append(path.relative_to(root).as_posix())
                continue
            if "localization" in path.parent.as_posix().lower() and path.suffix.lower() in self.localization_extensions:
                matched.append(path.relative_to(root).as_posix())
        return sorted(set(matched))

    def _collect_asset_files(self, base_dir: Path, root: Path) -> list[str]:
        matched = []
        for path in sorted(base_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in self.asset_extensions:
                matched.append(path.relative_to(root).as_posix())
        return matched

    def _read_engine_version(self, version_file: Path) -> str:
        if not version_file.exists():
            return ""
        for line in version_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("m_EditorVersion:"):
                return line.split(":", 1)[1].strip()
        return ""

    def _build_directory_tree(self, root: Path, max_depth: int = 2) -> str:
        lines = [root.name]
        for path in sorted(root.rglob("*")):
            relative_parts = path.relative_to(root).parts
            depth = len(relative_parts)
            if depth > max_depth:
                continue
            indent = "  " * (depth - 1)
            suffix = "/" if path.is_dir() else ""
            lines.append(f"{indent}- {relative_parts[-1]}{suffix}")
        return "\n".join(lines)
