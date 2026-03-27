from __future__ import annotations

import json
import sys
from pathlib import Path


DEFAULT_TARGET = Path(__file__).resolve().parent / "test_project"

PROJECT_FILES = {
    "Assets/Scenes/Main.unity": "%YAML 1.1\n# 示例场景文件\n",
    "Assets/Scripts/PlayerController.cs": (
        "using UnityEngine;\n\n"
        "public class PlayerController : MonoBehaviour\n"
        "{\n"
        "    [SerializeField] private float moveSpeed = 5f;\n\n"
        "    private void Update()\n"
        "    {\n"
        "        var horizontal = Input.GetAxis(\"Horizontal\");\n"
        "        transform.Translate(Vector3.right * horizontal * moveSpeed * Time.deltaTime);\n"
        "    }\n"
        "}\n"
    ),
    "Assets/Shaders/SimpleColor.shader": (
        "Shader \"Custom/SimpleColor\"\n"
        "{\n"
        "    Properties { _Color (\"Color\", Color) = (1,1,1,1) }\n"
        "    SubShader { Pass { } }\n"
        "}\n"
    ),
    "Assets/Resources/Configs/game_config.json": json.dumps(
        {"player_hp": 100, "player_speed": 5.0, "enemy_spawn_interval": 3.5},
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    "Assets/Localization/zh-CN.json": json.dumps(
        {"menu_start": "开始游戏", "menu_exit": "退出"},
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    "ProjectSettings/ProjectVersion.txt": "m_EditorVersion: 2022.3.21f1\n",
}


def create_project(target_dir: Path) -> None:
    for relative_path, content in PROJECT_FILES.items():
        file_path = target_dir / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")


def main() -> int:
    target_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_TARGET
    target_dir.mkdir(parents=True, exist_ok=True)
    create_project(target_dir)
    print(f"已创建测试 Unity 项目: {target_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
