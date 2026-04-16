import json
import re

from context.loader import build_system_prompt
from schemas.outputs import SubTaskPlan, try_parse


def build_plan_system_prompt(skill: dict, project_context: dict) -> str:
    base = build_system_prompt(skill, None, project_context)
    plan_instruction = """

## Planner 规划要求

你现在处于 Planner 阶段。目标是把用户需求拆解成可执行、可验证的 SubTaskPlan JSON。

输出格式必须严格遵守：

```json
{
  "subtasks": [
    {
      "step_id": 1,
      "description": "创建 XxxData.cs 数据类，包含字段...",
      "target_files": ["Assets/Scripts/Data/XxxData.cs"],
      "tool_hint": "write",
      "depends_on": []
    }
  ],
  "summary": "任务摘要"
}
```

规则：
1. 只输出 JSON，不要任何解释或 Markdown。
2. 子任务数量不超过 8 个。
3. description 必须具体、以动词开头，控制在 200 个字符以内。
4. target_files 必须使用项目根相对路径。
5. tool_hint 只能是 read / write / verify / mixed。
6. depends_on 按 step_id 填写。
7. 多文件任务优先按 数据类 -> 配置 -> 逻辑 -> UI -> 测试 顺序拆解。
8. 如果信息不足，可以调用只读工具；禁止调用 write_file。
"""
    return base + plan_instruction


def extract_json_payload(text: str):
    json_str = text
    match = re.search(r"```json\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        match = re.search(r"```\s*\n(.*?)\n\s*```", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                json_str = match.group(0)
    return json.loads(json_str)


def try_parse_plan(text: str) -> tuple[SubTaskPlan | None, str]:
    result, err = try_parse(text, SubTaskPlan)
    if result:
        return result, ""

    try:
        parsed = extract_json_payload(text)
        return SubTaskPlan(**parsed), ""
    except Exception:
        return None, err
