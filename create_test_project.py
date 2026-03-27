from __future__ import annotations

import json
from pathlib import Path


ROOT = Path("test_project")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    write(
        ROOT / "Assets" / "Scripts" / "PlayerController.cs",
        """using UnityEngine;

public class PlayerController : MonoBehaviour
{
    public float moveSpeed = 5f;

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Space))
        {
            Debug.Log("Jump");
        }
    }
}
""",
    )
    write(
        ROOT / "Assets" / "Scenes" / "Main.unity",
        "%YAML 1.1\n%TAG !u! tag:unity3d.com,2011:\n",
    )
    write(
        ROOT / "Assets" / "Configs" / "WeaponConfig.json",
        json.dumps(
            [
                {"id": 1001, "name": "铁剑", "damage": 50, "attackSpeed": 1.0},
                {"id": 1002, "name": "火焰剑", "damage": 100, "attackSpeed": 0.8},
            ],
            ensure_ascii=False,
            indent=2,
        ),
    )
    write(
        ROOT / "Assets" / "Prefabs" / "Player.prefab.meta",
        "fileFormatVersion: 2\nguid: abc123playerguid\n",
    )
    write(
        ROOT / "ProjectSettings" / "ProjectVersion.txt",
        "m_EditorVersion: 2022.3.20f1\n",
    )
    print(f"Created sample project at {ROOT.resolve()}")


if __name__ == "__main__":
    main()
