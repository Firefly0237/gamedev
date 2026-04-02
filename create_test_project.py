from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent


ROOT_DIR = Path(__file__).resolve().parent
TEST_PROJECT_DIR = ROOT_DIR / "test_project"

DIRECTORIES = [
    "Assets/Scripts/Player",
    "Assets/Scripts/Systems",
    "Assets/Scripts/Data",
    "Assets/Scripts/UI",
    "Assets/Scenes",
    "Assets/Prefabs/Characters",
    "Assets/Shaders",
    "Assets/Resources/Configs",
    "Assets/Resources/Localization",
    "Assets/Art/Sprites",
    "Assets/Art/UI",
    "Assets/Tests/Editor",
    "Assets/Editor",
    "ProjectSettings",
]


def write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")


def write_empty_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def create_directories() -> None:
    for relative_dir in DIRECTORIES:
        (TEST_PROJECT_DIR / relative_dir).mkdir(parents=True, exist_ok=True)


def create_project_settings() -> None:
    write_text_file(
        TEST_PROJECT_DIR / "ProjectSettings" / "ProjectVersion.txt",
        """
        m_EditorVersion: 2022.3.20f1
        """,
    )


def create_scripts() -> None:
    write_text_file(
        TEST_PROJECT_DIR / "Assets" / "Scripts" / "Player" / "PlayerController.cs",
        """
        using UnityEngine;

        namespace MyGame.Player
        {
            public class PlayerController : MonoBehaviour
            {
                public float moveSpeed = 5f;
                public float jumpForce = 7f;
                public int maxHealth = 100;

                private int _currentHealth;

                private void Start()
                {
                    _currentHealth = maxHealth;
                }

                private void Update()
                {
                    Rigidbody2D rb = GetComponent<Rigidbody2D>();
                    if (gameObject.tag == "Player")
                    {
                        Camera mainCamera = Camera.main;
                        if (mainCamera != null && rb != null)
                        {
                            rb.linearVelocity = new Vector2(moveSpeed, rb.linearVelocity.y);
                        }
                    }
                }

                public void TakeDamage(int damage)
                {
                    _currentHealth -= damage;
                    if (_currentHealth <= 0)
                    {
                        Die();
                    }
                }

                public int GetCurrentHealth()
                {
                    return _currentHealth;
                }

                public float GetHealthPercentage()
                {
                    return maxHealth <= 0 ? 0f : (float)_currentHealth / maxHealth;
                }

                private void Die()
                {
                    gameObject.SetActive(false);
                }
            }
        }
        """,
    )

    write_text_file(
        TEST_PROJECT_DIR / "Assets" / "Scripts" / "Systems" / "DamageCalculator.cs",
        """
        using UnityEngine;

        namespace MyGame.Systems
        {
            public class DamageCalculator
            {
                /// <summary>
                /// Calculates the final damage after defense reduction.
                /// </summary>
                public float CalculateDamage(float baseDamage, float defense)
                {
                    return Mathf.Max(baseDamage - defense, 1f);
                }

                /// <summary>
                /// Calculates critical damage with a minimum multiplier of 1.
                /// </summary>
                public float CalculateCritical(float damage, float critMultiplier)
                {
                    return damage * Mathf.Max(critMultiplier, 1f);
                }

                /// <summary>
                /// Calculates elemental damage using the given bonus value.
                /// </summary>
                public float CalculateElementalDamage(float damage, float elementBonus)
                {
                    return damage * (1f + elementBonus);
                }
            }
        }
        """,
    )

    write_text_file(
        TEST_PROJECT_DIR / "Assets" / "Scripts" / "Data" / "WeaponData.cs",
        """
        using UnityEngine;

        namespace MyGame.Data
        {
            public enum WeaponType
            {
                Sword,
                Bow,
                Staff,
                Dagger,
                Hammer
            }

            public enum Rarity
            {
                Common,
                Uncommon,
                Rare,
                Epic,
                Legendary
            }

            [CreateAssetMenu(fileName = "WeaponData", menuName = "MyGame/Weapon Data")]
            public class WeaponData : ScriptableObject
            {
                public int id;
                public string weaponName = "";
                public WeaponType weaponType;
                public Rarity rarity;
                public int damage;
                public float attackSpeed;
                public float critRate;
                public string description = "";
            }
        }
        """,
    )


def create_assets() -> None:
    write_text_file(
        TEST_PROJECT_DIR / "Assets" / "Shaders" / "ToonWater.shader",
        """
        Shader "Custom/ToonWater"
        {
            SubShader
            {
                Pass
                {
                }
            }
        }
        """,
    )

    write_text_file(
        TEST_PROJECT_DIR / "Assets" / "Resources" / "Configs" / "WeaponConfig.json",
        """
        {
          "items": [
            {"id": 1001, "name": "铁剑", "weaponType": "Sword", "damage": 50, "rarity": "Common", "price": 100},
            {"id": 1002, "name": "火焰剑", "weaponType": "Sword", "damage": 100, "rarity": "Rare", "price": 500},
            {"id": 1003, "name": "长弓", "weaponType": "Bow", "damage": 70, "rarity": "Uncommon", "price": 200}
          ]
        }
        """,
    )

    write_text_file(
        TEST_PROJECT_DIR / "Assets" / "Resources" / "Configs" / "GameConfig.json",
        """
        {"version": "1.0", "maxLevel": 50, "startingGold": 100}
        """,
    )

    write_text_file(
        TEST_PROJECT_DIR / "Assets" / "Resources" / "Localization" / "zh-CN.json",
        """
        {
          "greeting": "你好，冒险者！",
          "farewell": "再见",
          "attack": "攻击",
          "defense": "防御",
          "hp_display": "生命值: {0}/{1}",
          "level_up": "{player_name} 升级了！",
          "shop_buy": "购买 {item_name} 需要 {price} 金币"
        }
        """,
    )

    for scene_name in ("MainMenu.unity", "Level1.unity", "BossArena.unity"):
        write_empty_file(TEST_PROJECT_DIR / "Assets" / "Scenes" / scene_name)

    for prefab_name in ("Player.prefab", "Goblin.prefab"):
        write_empty_file(TEST_PROJECT_DIR / "Assets" / "Prefabs" / "Characters" / prefab_name)


def init_git_repo() -> None:
    commands = [
        ["git", "init"],
        ["git", "add", "."],
        ["git", "commit", "-m", "Initial test project"],
    ]

    for command in commands:
        result = subprocess.run(
            command,
            cwd=TEST_PROJECT_DIR,
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
        )
        if result.returncode != 0:
            print(f"Git command failed: {' '.join(command)}")
            if result.stderr.strip():
                print(result.stderr.strip())
            return


def main() -> None:
    create_directories()
    create_project_settings()
    create_scripts()
    create_assets()
    init_git_repo()
    print(f"Test project created at: {TEST_PROJECT_DIR}")


if __name__ == "__main__":
    main()
