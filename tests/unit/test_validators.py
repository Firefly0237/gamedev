"""validators 的单元测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from graphs.validators import validate_all_configs, validate_config_file


pytestmark = pytest.mark.unit


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class TestValidateConfigFile:
    def test_duplicate_ids_detected(self, tmp_path):
        file_path = tmp_path / "dup.json"
        _write_json(
            file_path,
            [{"id": 1, "name": "A", "damage": 10}, {"id": 1, "name": "B", "damage": 20}],
        )
        issues = validate_config_file(str(file_path))
        assert any("ID 重复" in issue["message"] for issue in issues)

    def test_negative_and_probability_issues(self, tmp_path):
        file_path = tmp_path / "bad_values.json"
        _write_json(
            file_path,
            [{"id": 1, "name": "Sword", "damage": -5, "critRate": 1.5, "description": ""}],
        )
        issues = validate_config_file(str(file_path))
        messages = " ".join(issue["message"] for issue in issues)
        assert "不应为负数" in messages
        assert "应在 [0, 1]" in messages
        assert "不应为空字符串" in messages

    def test_schema_missing_field_and_type_mismatch(self, tmp_path):
        file_path = tmp_path / "schema.json"
        _write_json(file_path, [{"id": "1", "name": "Sword"}])
        schema = {"sample_record": {"id": 1, "name": "Sword", "damage": 10}}
        issues = validate_config_file(str(file_path), schema)
        messages = " ".join(issue["message"] for issue in issues)
        assert "缺少字段 damage" in messages
        assert "类型不一致" in messages


class TestValidateAllConfigs:
    def test_collects_project_json_files(self, tmp_path):
        project = tmp_path / "project"
        file_path = project / "Assets" / "Resources" / "Configs" / "GameConfig.json"
        _write_json(file_path, [{"id": 1, "name": "", "damage": -1}])

        result = validate_all_configs(str(project), schemas=[])
        assert result["total_files"] == 1
        assert result["total_issues"] >= 2
        rel_path = "Assets/Resources/Configs/GameConfig.json"
        assert rel_path in result["by_file"]
