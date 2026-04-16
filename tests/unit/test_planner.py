"""Planner 解析测试。"""

import pytest

from context.loader import load_skill
from graphs.orchestrator.planner import run_planner
from tests.fixtures.mock_responses import subtask_plan_simple


pytestmark = pytest.mark.unit


class TestPlanner:
    def test_run_planner_returns_valid_subtask_plan(self, scanned_context, mock_llm):
        mock_llm.set_responses([subtask_plan_simple()], task_type="plan")
        skill = load_skill("generate_system")

        plan, tokens, err, llm_info = run_planner("做一个测试系统", skill, scanned_context)

        assert err == ""
        assert tokens > 0
        assert plan is not None
        assert plan.summary == "测试用的 mock 系统"
        assert len(plan.subtasks) == 2
        assert llm_info.task_type == "plan"
