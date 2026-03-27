from __future__ import annotations

import difflib
import shutil
import subprocess
from pathlib import Path


def ensure_parent_directory(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def create_backup(file_path: Path) -> Path:
    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
    shutil.copy2(file_path, backup_path)
    return backup_path


def preview_diff(old_text: str, new_text: str, file_name: str) -> str:
    diff = difflib.unified_diff(
        old_text.splitlines(),
        new_text.splitlines(),
        fromfile=f"{file_name} (old)",
        tofile=f"{file_name} (new)",
        lineterm="",
    )
    return "\n".join(diff)


def git_auto_save(project_root: Path, message: str = "GameDev auto-save") -> dict[str, str]:
    if not (project_root / ".git").exists():
        return {"status": "skipped", "message": "No git repository found."}
    try:
        subprocess.run(["git", "add", "-A"], cwd=project_root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", message], cwd=project_root, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        return {"status": "failed", "message": exc.stderr.strip() or exc.stdout.strip()}
    return {"status": "success", "message": message}
