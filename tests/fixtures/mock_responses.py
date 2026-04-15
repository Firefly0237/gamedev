"""预录的 mock LLM 响应。"""


def config_modify_single() -> str:
    return """```json
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
  "summary": "火焰剑攻击力 100 → 150"
}
```"""


def config_batch_modify() -> str:
    return """```json
{
  "actions": [
    {
      "file_path": "Assets/Resources/Configs/WeaponConfig.json",
      "filter": {},
      "operation": "multiply",
      "target_field": "damage",
      "value": 1.1
    }
  ],
  "summary": "所有武器攻击力提升 10%"
}
```"""


def code_modify_single() -> str:
    return """```json
{
  "actions": [
    {
      "file_path": "Assets/Scripts/Player/PlayerController.cs",
      "search_pattern": "public float moveSpeed = 5f;",
      "replace_with": "public float moveSpeed = 8f;"
    }
  ],
  "summary": "moveSpeed 从 5 改为 8"
}
```"""


def subtask_plan_simple() -> str:
    return """```json
{
  "subtasks": [
    {
      "step_id": 1,
      "description": "创建 TestDataMock.cs 数据类,包含 id 和 name 字段",
      "target_files": ["Assets/Scripts/Data/TestDataMock.cs"],
      "tool_hint": "write",
      "depends_on": []
    },
    {
      "step_id": 2,
      "description": "创建 TestConfigMock.json 配置文件",
      "target_files": ["Assets/Resources/Configs/TestConfigMock.json"],
      "tool_hint": "write",
      "depends_on": [1]
    }
  ],
  "summary": "测试用的 mock 系统"
}
```"""
