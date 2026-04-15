"""配置修改的真实 e2e 测试。"""

from __future__ import annotations

import json
import os

import pytest

from context.loader import load_skill, match_schema
from graphs.deterministic import run_config_modify


pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.timeout(180)]


class TestConfigModifyE2E:
    def test_single_modify_real_llm(self, mcp_initialized, scanned_context, test_project_path):
        _ = mcp_initialized
        skill = load_skill("modify_config")
        schema = match_schema("火焰剑")

        weapon_path = os.path.join(test_project_path, "Assets/Resources/Configs/WeaponConfig.json")
        if not os.path.exists(weapon_path):
            pytest.skip("test_project 没有 WeaponConfig.json")

        with open(weapon_path, encoding="utf-8") as file_obj:
            original = file_obj.read()

        try:
            result = run_config_modify(
                "把火焰剑攻击力改到150",
                skill,
                schema,
                scanned_context,
            )
            assert result["status"] == "success"

            data = json.loads(open(weapon_path, encoding="utf-8").read())
            sword = next((item for item in data if item.get("name") == "火焰剑"), None)
            assert sword is not None
            assert sword["damage"] == 150
        finally:
            with open(weapon_path, "w", encoding="utf-8") as file_obj:
                file_obj.write(original)
