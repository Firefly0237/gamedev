"""Deterministic 执行器的集成测试(mock LLM)。"""

from __future__ import annotations

import json
import os

import pytest

from context.loader import load_skill, match_schema
from graphs.deterministic import run_config_modify
from tests.fixtures.mock_responses import config_modify_single


pytestmark = pytest.mark.integration


class TestConfigModifyWithMockLLM:
    def test_single_modify_flow(self, mcp_initialized, scanned_context, mock_llm, test_project_path):
        _ = mcp_initialized
        mock_llm.set_responses([config_modify_single()])

        skill = load_skill("modify_config")
        schema = match_schema("火焰剑")

        weapon_path = os.path.join(test_project_path, "Assets/Resources/Configs/WeaponConfig.json")
        if not os.path.exists(weapon_path):
            pytest.skip("test_project 没有 WeaponConfig.json")

        original = open(weapon_path, encoding="utf-8").read()

        try:
            result = run_config_modify(
                "把火焰剑攻击力改到150",
                skill,
                schema,
                scanned_context,
            )
            assert "status" in result
            assert "route" in result
            assert result["route"] == "deterministic"
            assert "verification" in result
            assert "output_files" in result

            if result["status"] == "success":
                data = json.loads(open(weapon_path, encoding="utf-8").read())
                sword = next((item for item in data if item.get("name") == "火焰剑"), None)
                assert sword is not None
                assert sword["damage"] == 150
        finally:
            with open(weapon_path, "w", encoding="utf-8") as file_obj:
                file_obj.write(original)
