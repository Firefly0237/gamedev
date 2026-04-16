import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.llm import resolve_task_model


TASK_TYPES = [
    "intent_parse",
    "routing",
    "review",
    "translate",
    "generation",
    "fix_loop",
    "plan",
    "requirement",
]


def main():
    for task_type in TASK_TYPES:
        try:
            info = resolve_task_model(task_type)
            print(f"{task_type:15s} -> {info.provider}/{info.model}")
        except Exception as exc:
            print(f"{task_type:15s} -> ERROR: {exc}")


if __name__ == "__main__":
    main()
