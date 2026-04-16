from __future__ import annotations

from functools import lru_cache

from ._base import WorkerSpec, build_worker_agent


CONFIG_AGENT_STUB_PROMPT = """你是 config_agent 的占位版本。

当前版本尚未实现配置文件批量编辑与结构化校验自动化。
无论收到什么请求，都只输出一个 JSON 对象，不要调用任何工具：
{
  "worker": "config_agent",
  "status": "failed",
  "summary": "config_agent 当前尚未实装",
  "created_files": [],
  "error_code": "NOT_IMPLEMENTED",
  "error_details": "该能力仍在规划中，请改派 code_agent 或提示用户。"
}
"""


SPEC = WorkerSpec(
    name="config_agent",
    description="处理 JSON / YAML / 配置表结构化修改。当前为 stub。",
    tools=[],
    system_prompt=CONFIG_AGENT_STUB_PROMPT,
    task_type="routing",
    enabled=False,
    tool_profile="config_agent",
)


@lru_cache(maxsize=1)
def get_agent():
    return build_worker_agent(SPEC)
