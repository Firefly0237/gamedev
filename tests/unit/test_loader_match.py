"""loader 的匹配测试。"""

import pytest

from context.loader import (
    build_system_prompt,
    extract_focus_class,
    load_all_skills,
    load_skill,
    match_schema,
    match_skill,
)


pytestmark = pytest.mark.unit


class TestLoaderMatch:
    def test_load_all_skills(self):
        skills = load_all_skills()
        assert len(skills) >= 10

    def test_match_review_skill(self):
        skill = match_skill("审查 PlayerController")
        assert skill is not None
        assert skill["skill_id"] == "review_code"

    def test_match_build_skill(self):
        skill = match_skill("编译项目")
        assert skill is not None
        assert skill["skill_id"] == "validate_build"

    def test_match_generate_test_skill(self):
        skill = match_skill("为 DamageCalculator 生成测试")
        assert skill is not None
        assert skill["skill_id"] == "generate_test"

    def test_load_skill_route_from_yaml(self):
        skill = load_skill("generate_system")
        assert skill is not None
        assert skill["route"] == "orchestrator"

    def test_extract_focus_class(self, scanned_context):
        assert extract_focus_class("审查 PlayerController 的性能问题", scanned_context) == "PlayerController"

    def test_match_schema(self, scanned_context):
        _ = scanned_context
        schema = match_schema("把火焰剑攻击力改到150")
        assert schema is not None
        assert schema["file_path"].endswith("WeaponConfig.json")

    def test_build_system_prompt_includes_focus_and_skill(self, scanned_context):
        skill = load_skill("review_code")
        prompt = build_system_prompt(skill, None, scanned_context, focus_class="PlayerController")
        assert "PlayerController" in prompt
        assert "代码审查" in prompt
