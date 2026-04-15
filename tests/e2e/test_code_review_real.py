"""代码审查真实 e2e 测试。"""

from __future__ import annotations

import pytest

from context.loader import load_skill
from graphs.agent_loop import run_agent_loop


pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.timeout(180)]


class TestCodeReviewE2E:
    def test_review_player_controller(self, mcp_initialized, scanned_context):
        _ = mcp_initialized
        skill = load_skill("review_code")
        result = run_agent_loop(
            "审查 PlayerController 的性能和规范问题",
            skill=skill,
            project_context=scanned_context,
            verify_mode="off",
        )
        assert result["status"] == "success"
        assert result["route"] == "agent_loop"
        assert result["display"]
