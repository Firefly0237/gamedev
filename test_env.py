from __future__ import annotations

import importlib
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
REQUIRED_MODULES = [
    "streamlit",
    "dotenv",
    "langchain",
    "langgraph",
]
OPTIONAL_ENV_KEYS = [
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "UNITY_PROJECT_PATH",
]


def check_modules() -> list[str]:
    missing = []
    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(module_name)
    return missing


def check_env() -> dict[str, bool]:
    return {key: bool(os.getenv(key, "").strip()) for key in OPTIONAL_ENV_KEYS}


def main() -> int:
    print("GameDev 环境检查")
    print(f"项目目录: {BASE_DIR}")

    missing_modules = check_modules()
    if missing_modules:
        print("缺少依赖模块:")
        for module_name in missing_modules:
            print(f"  - {module_name}")
    else:
        print("依赖模块检查通过。")

    env_status = check_env()
    print("环境变量状态:")
    for key, is_set in env_status.items():
        print(f"  - {key}: {'已设置' if is_set else '未设置'}")

    expected_paths = [
        BASE_DIR / "app.py",
        BASE_DIR / "pages",
        BASE_DIR / "context" / "patterns",
        BASE_DIR / "logs",
    ]
    print("目录结构检查:")
    for path in expected_paths:
        print(f"  - {path}: {'存在' if path.exists() else '缺失'}")

    if missing_modules:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
