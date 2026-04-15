"""test_project 自带生成器。

这个文件故意不依赖被忽略的 create_test_project.py，
保证 CI 在干净仓库里也能重建测试夹具。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent


PLAYER_CONTROLLER_CS = dedent(
    """\
    using UnityEngine;

    namespace MyGame.Player
    {
        public class PlayerController : MonoBehaviour
        {
            public float moveSpeed = 5f;
            public float jumpForce = 10f;
            public int maxHealth = 100;
            private int currentHealth;

            void Update()
            {
                var rb = GetComponent<Rigidbody>();
                float h = Input.GetAxis("Horizontal");
                float v = Input.GetAxis("Vertical");
                rb.velocity = new Vector3(h * moveSpeed, rb.velocity.y, v * moveSpeed);

                Camera.main.transform.position = transform.position + new Vector3(0, 10, -10);

                if (transform.position.y < -50)
                {
                    currentHealth -= 10;
                }

                if (gameObject.tag == "Player")
                {
                    Debug.Log("Player is alive: " + currentHealth + "/" + maxHealth);
                }
            }

            public void TakeDamage(int damage)
            {
                currentHealth -= damage;
                if (currentHealth <= 0)
                {
                    Die();
                }
            }

            void Die()
            {
                Destroy(gameObject);
            }
        }
    }
    """
)

PLAYER_CONTROLLER_META = dedent(
    """\
    fileFormatVersion: 2
    guid: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4
    MonoImporter:
      serializedVersion: 2
      defaultReferences: []
      executionOrder: 0
      icon: {instanceID: 0}
      userData:
      assetBundleName:
      assetBundleVariant:
    """
)

DAMAGE_CALCULATOR_CS = dedent(
    """\
    namespace MyGame.Combat
    {
        public static class DamageCalculator
        {
            public static int CalculateDamage(int baseDamage, float critRate)
            {
                return critRate > 0.5f ? baseDamage * 2 : baseDamage;
            }
        }
    }
    """
)

HEALTH_BAR_CS = dedent(
    """\
    using UnityEngine;
    using UnityEngine.UI;

    namespace MyGame.UI
    {
        public class HealthBar : MonoBehaviour
        {
            public Slider slider;

            public void SetValue(float value)
            {
                if (slider != null)
                {
                    slider.value = value;
                }
            }
        }
    }
    """
)

TOON_LIT_SHADER = dedent(
    """\
    Shader "MyGame/ToonLit"
    {
        Properties
        {
            _Color ("Color", Color) = (1,1,1,1)
        }
        SubShader
        {
            Tags { "RenderType"="Opaque" }
            Pass
            {
                CGPROGRAM
                #pragma vertex vert
                #pragma fragment frag
                struct appdata { float4 vertex : POSITION; };
                struct v2f { float4 pos : SV_POSITION; };
                v2f vert(appdata v) { v2f o; o.pos = v.vertex; return o; }
                fixed4 frag(v2f i) : SV_Target { return fixed4(1,1,1,1); }
                ENDCG
            }
        }
    }
    """
)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, content: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")


def _on_remove_error(func, path, exc_info):
    """Windows 下删除只读文件时兜底改权限后重试。"""
    try:
        os.chmod(path, 0o666)
        func(path)
    except Exception:
        raise exc_info[1]


def _create_files(test_project: Path) -> None:
    write_text(test_project / "Assets" / "Scripts" / "Player" / "PlayerController.cs", PLAYER_CONTROLLER_CS)
    write_text(test_project / "Assets" / "Scripts" / "Player" / "PlayerController.cs.meta", PLAYER_CONTROLLER_META)
    write_text(test_project / "Assets" / "Scripts" / "Combat" / "DamageCalculator.cs", DAMAGE_CALCULATOR_CS)
    write_text(test_project / "Assets" / "Scripts" / "UI" / "HealthBar.cs", HEALTH_BAR_CS)
    write_text(test_project / "Assets" / "Shaders" / "ToonLit.shader", TOON_LIT_SHADER)

    write_json(
        test_project / "Assets" / "Resources" / "Configs" / "WeaponConfig.json",
        [
            {"id": 1, "name": "木剑", "damage": 50, "price": 100, "type": "Common"},
            {"id": 2, "name": "火焰剑", "damage": 100, "price": 300, "type": "Rare"},
            {"id": 3, "name": "冰霜剑", "damage": 70, "price": 180, "type": "Common"},
        ],
    )
    write_json(
        test_project / "Assets" / "Resources" / "Configs" / "GameConfig.json",
        {"playerName": "Hero", "startGold": 100, "difficulty": "Normal"},
    )
    write_json(
        test_project / "Assets" / "Resources" / "Localization" / "zh-CN.json",
        {"ui.start": "开始游戏", "ui.exit": "退出", "weapon.fire_sword": "火焰剑"},
    )

    for scene_name in ("MainMenu", "Level1", "Level2"):
        write_text(
            test_project / "Assets" / "Scenes" / f"{scene_name}.unity",
            f"%YAML 1.1\n--- !u!1 &1\nGameObject:\n  m_Name: {scene_name}\n",
        )

    write_text(
        test_project / "ProjectSettings" / "ProjectVersion.txt",
        "m_EditorVersion: 2022.3.10f1\nm_EditorVersionWithRevision: 2022.3.10f1 (mock)\n",
    )
    write_text(test_project / "ProjectSettings" / "PhysicsManager.asset", "m_Gravity: {x: 0, y: -9.81, z: 0}\n")
    write_text(test_project / "ProjectSettings" / "QualitySettings.asset", "m_CurrentQuality: 2\n")


def _init_git_repo(test_project: Path) -> None:
    subprocess.run(["git", "init"], cwd=str(test_project), check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(test_project), check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=GameDev Test", "-c", "user.email=test@example.com", "commit", "-m", "Initial test project"],
        cwd=str(test_project),
        check=True,
        capture_output=True,
    )


def rebuild_test_project(project_root: Path) -> str:
    project_root = Path(project_root)
    test_project = project_root / "test_project"
    if test_project.exists():
        shutil.rmtree(test_project, onexc=_on_remove_error)

    _create_files(test_project)
    _init_git_repo(test_project)
    return str(test_project)


def ensure_test_project(project_root: Path) -> str:
    project_root = Path(project_root)
    test_project = project_root / "test_project"
    if not test_project.exists():
        return rebuild_test_project(project_root)
    return str(test_project)


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    print(rebuild_test_project(project_root))


if __name__ == "__main__":
    main()
