from __future__ import annotations

from pathlib import Path


def read_project_settings(project_path: str, settings_file: str) -> dict:
    project_root = Path(project_path).resolve()
    settings_dir = project_root / "ProjectSettings"
    if not settings_dir.exists():
        return {"success": False, "message": "ProjectSettings 目录不存在", "available_files": []}

    path = settings_dir / settings_file
    if not path.exists():
        available = sorted(item.name for item in settings_dir.iterdir() if item.is_file())
        return {
            "success": False,
            "message": f"文件不存在: {settings_file}",
            "available_files": available,
        }

    content = path.read_text(encoding="utf-8", errors="ignore")
    return {
        "success": True,
        "path": str(path.relative_to(project_root)).replace("\\", "/"),
        "content": content[:5000],
    }
