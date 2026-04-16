from __future__ import annotations

from functools import lru_cache

from ._base import WorkerSpec, build_worker_agent


ART_AGENT_STUB_PROMPT = """你是 art_agent 的占位版本。

当前版本尚未实现 Texture / Material / Prefab / Sprite 资源自动处理。
无论收到什么请求，都只输出一个 JSON 对象，不要调用任何工具：
{
  "worker": "art_agent",
  "status": "failed",
  "summary": "art_agent 当前尚未实装",
  "created_files": [],
  "error_code": "NOT_IMPLEMENTED",
  "error_details": "该能力仍在规划中，请改派 code_agent 或提示用户。"
}
"""


SPEC = WorkerSpec(
    name="art_agent",
    description="处理贴图、材质、Prefab、Sprite Atlas 等美术资源。当前为 stub。",
    tools=[],
    system_prompt=ART_AGENT_STUB_PROMPT,
    task_type="routing",
    enabled=False,
    tool_profile="art_agent",
)


@lru_cache(maxsize=1)
def get_agent():
    return build_worker_agent(SPEC)
