"""输出模型的单元测试。"""

import pytest

from schemas.outputs import (
    CodeModifyPlan,
    ConfigBatchPlan,
    ConfigModifyPlan,
    SubTaskPlan,
    try_parse,
)


pytestmark = pytest.mark.unit


class TestOutputsSchemas:
    def test_config_modify_plan_parses(self):
        text = """```json
{
  "actions": [
    {
      "file_path": "Assets/Resources/Configs/WeaponConfig.json",
      "match_field": "name",
      "match_value": "火焰剑",
      "target_field": "damage",
      "old_value": 100,
      "new_value": 150
    }
  ],
  "summary": "火焰剑攻击力提升"
}
```"""
        result, err = try_parse(text, ConfigModifyPlan)
        assert err == ""
        assert result is not None
        assert result.actions[0].new_value == 150

    def test_config_batch_plan_parses(self):
        text = """{
  "actions": [
    {
      "file_path": "Assets/Resources/Configs/WeaponConfig.json",
      "filter": {},
      "operation": "multiply",
      "target_field": "damage",
      "value": 1.1
    }
  ],
  "summary": "批量修改"
}"""
        result, err = try_parse(text, ConfigBatchPlan)
        assert err == ""
        assert result.actions[0].operation == "multiply"

    def test_code_modify_plan_rejects_short_search_pattern(self):
        text = """{
  "actions": [
    {
      "file_path": "Assets/Scripts/Foo.cs",
      "search_pattern": "ab",
      "replace_with": "xyz"
    }
  ],
  "summary": "bad"
}"""
        result, err = try_parse(text, CodeModifyPlan)
        assert result is None
        assert "校验失败" in err

    def test_subtask_plan_parses_dependencies(self):
        text = """{
  "subtasks": [
    {
      "step_id": 1,
      "description": "创建 FooData.cs 数据类，包含 id 和 name 字段",
      "target_files": ["Assets/Scripts/Data/FooData.cs"],
      "tool_hint": "write",
      "depends_on": []
    },
    {
      "step_id": 2,
      "description": "创建 FooConfig.json 配置文件，包含 3 个示例数据",
      "target_files": ["Assets/Resources/Configs/FooConfig.json"],
      "tool_hint": "write",
      "depends_on": [1]
    }
  ],
  "summary": "foo system"
}"""
        result, err = try_parse(text, SubTaskPlan)
        assert err == ""
        assert result.subtasks[1].depends_on == [1]

    def test_try_parse_invalid_json(self):
        result, err = try_parse("not json", ConfigModifyPlan)
        assert result is None
        assert "JSON 解析失败" in err
