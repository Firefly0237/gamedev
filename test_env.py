from __future__ import annotations

import importlib

from config.settings import get_settings


def check_module(name: str) -> str:
    try:
        importlib.import_module(name)
        return "ok"
    except Exception as exc:  # pragma: no cover - diagnostic script
        return f"missing: {exc}"


def main() -> None:
    settings = get_settings()
    print(f"app_name={settings.app_name}")
    print(f"database={settings.database_file}")
    print(f"checkpoint={settings.checkpoint_file}")
    for module in ["streamlit", "pydantic", "langgraph", "requests"]:
        print(f"{module}={check_module(module)}")


if __name__ == "__main__":
    main()
