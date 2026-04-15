"""ExecutionResult 和 SafetyPolicy 契约测试。"""

import pytest

from schemas.contracts import (
    default_safety_policy,
    empty_result,
    infer_task_type,
    infer_validator,
)


pytestmark = pytest.mark.unit


class TestEmptyResult:
    def test_contains_all_required_fields(self):
        result = empty_result(route="deterministic", task_id=1)
        required = [
            "status",
            "route",
            "display",
            "summary",
            "output_files",
            "actions",
            "steps",
            "verification",
            "tokens",
            "duration",
            "error",
            "task_id",
        ]
        for field in required:
            assert field in result

    def test_default_status_is_failed(self):
        assert empty_result()["status"] == "failed"

    def test_verification_defaults_to_dict(self):
        verification = empty_result()["verification"]
        assert isinstance(verification, dict)
        assert verification["performed"] is False
        assert verification["details"] == []


class TestSafetyPolicy:
    def test_modify_requires_confirm(self):
        policy = default_safety_policy("modify")
        assert policy["require_confirm"] is True
        assert policy["diff_preview"] is True

    def test_review_does_not_require_confirm(self):
        policy = default_safety_policy("review")
        assert policy["require_confirm"] is False

    def test_generate_has_backup(self):
        policy = default_safety_policy("generate")
        assert policy["auto_backup"] is True
        assert policy["git_auto_save"] is False


class TestTaskTypeInfer:
    @pytest.mark.parametrize(
        ("skill_id", "expected"),
        [
            ("modify_config", "modify"),
            ("modify_code", "modify"),
            ("review_code", "review"),
            ("generate_test", "generate"),
            ("generate_system", "generate"),
            ("translate", "translate"),
            ("unknown_skill", "analyze"),
        ],
    )
    def test_infer_task_type(self, skill_id, expected):
        assert infer_task_type(skill_id) == expected


class TestValidatorInfer:
    def test_modify_config_has_validator(self):
        assert infer_validator("modify_config") == "ConfigModifyPlan"

    def test_generate_test_has_no_validator(self):
        assert infer_validator("generate_test") is None
