"""task_type 路由测试。"""

import pytest

from graphs.agent_loop import resolve_skill_task_type


pytestmark = pytest.mark.unit


def test_agent_loop_skill_task_type_mapping():
    assert resolve_skill_task_type("review_code") == "review"
    assert resolve_skill_task_type("generate_test") == "generation"
    assert resolve_skill_task_type("modify_code") == "intent_parse"
    assert resolve_skill_task_type("summarize_requirement") == "requirement"
    assert resolve_skill_task_type("unknown-skill") == "review"
