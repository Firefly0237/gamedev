from __future__ import annotations

import json
from pathlib import Path


COPLAY_PACKAGE_NAME = "com.coplaydev.unity-mcp"


def detect_coplay_package(project_path: str) -> dict:
    project_root = Path(project_path).resolve()
    manifest_path = project_root / "Packages" / "manifest.json"
    is_unity_project = (project_root / "Assets").exists() and (project_root / "ProjectSettings").exists()

    result = {
        "is_unity_project": is_unity_project,
        "package_installed": False,
        "package_name": COPLAY_PACKAGE_NAME,
        "manifest_path": str(manifest_path),
        "reason": "",
    }

    if not is_unity_project:
        result["reason"] = "不是 Unity 项目"
        return result

    if not manifest_path.exists():
        result["reason"] = "缺少 Packages/manifest.json"
        return result

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        result["reason"] = f"manifest.json 读取失败: {exc}"
        return result

    dependencies = manifest.get("dependencies", {})
    if COPLAY_PACKAGE_NAME in dependencies:
        result["package_installed"] = True
        return result

    result["reason"] = f"未安装 {COPLAY_PACKAGE_NAME}"
    return result
