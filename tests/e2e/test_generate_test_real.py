"""测试生成真实 e2e 测试。"""

from __future__ import annotations

import os

import pytest

from context.loader import load_skill
from graphs.agent_loop import run_agent_loop


pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.timeout(180)]


class TestGenerateTestE2E:
    def test_generate_damage_calculator_tests(self, mcp_initialized, scanned_context, test_project_path, cleanup_generated_files):
        _ = mcp_initialized
        skill = load_skill("generate_test")
        result = run_agent_loop(
            "为 DamageCalculator 生成测试",
            skill=skill,
            project_context=scanned_context,
        )

        for rel_path in result.get("output_files", []):
            cleanup_generated_files.append(rel_path)

        assert result["status"] == "success"
        assert result["verification"]["performed"] is True
        assert result["verification"]["passed"] is True

        expected = "Assets/Tests/Editor/DamageCalculatorTests.cs"
        assert expected in result["output_files"]
        assert os.path.isfile(os.path.join(test_project_path, expected))
