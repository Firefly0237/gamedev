"""Router 分类的集成测试。"""

import pytest

from graphs.router import classify_intent


pytestmark = pytest.mark.integration


class TestClassifyIntent:
    def test_modify_config_route(self, scanned_context, mcp_initialized):
        _ = mcp_initialized
        result = classify_intent("把火焰剑攻击力改到150", scanned_context)
        assert result["route"] == "deterministic"
        assert result["skill_id"] == "modify_config"
        assert result["task_type"] == "modify"

    def test_review_route(self, scanned_context, mcp_initialized):
        _ = mcp_initialized
        result = classify_intent("审查 PlayerController", scanned_context)
        assert result["route"] == "agent_loop"
        assert result["skill_id"] == "review_code"

    def test_supervisor_route(self, scanned_context, mcp_initialized):
        _ = mcp_initialized
        result = classify_intent("做一个背包系统", scanned_context)
        assert result["route"] == "supervisor"

    def test_batch_detection(self, scanned_context, mcp_initialized):
        _ = mcp_initialized
        result = classify_intent("所有武器攻击力提升10%", scanned_context)
        assert result["route"] == "deterministic"
        assert result.get("is_batch") is True

    def test_returns_all_contract_fields(self, scanned_context, mcp_initialized):
        _ = mcp_initialized
        result = classify_intent("审查代码", scanned_context)
        for field in ["route", "skill", "schema", "skill_id", "task_type", "validator", "safety_policy"]:
            assert field in result
