"""art_agent stub 行为测试。"""

from __future__ import annotations

import json

import pytest
from langchain_core.messages import HumanMessage

from graphs.orchestrator.workers import art_agent


pytestmark = pytest.mark.integration


class TestArtAgentStub:
    def test_art_agent_returns_not_implemented(self, mock_llm):
        mock_llm.set_responses(
            [
                {
                    "content": json.dumps(
                        {
                            "worker": "art_agent",
                            "status": "failed",
                            "summary": "art_agent 当前尚未实装",
                            "created_files": [],
                            "error_code": "NOT_IMPLEMENTED",
                            "error_details": "stub",
                        },
                        ensure_ascii=False,
                    )
                }
            ],
            task_type="routing",
        )

        graph = art_agent.get_agent()
        result = graph.invoke({"messages": [HumanMessage(content="生成一张 Texture")]})
        message = result["messages"][-1]
        payload = json.loads(message.content)

        assert payload["worker"] == "art_agent"
        assert payload["error_code"] == "NOT_IMPLEMENTED"
        assert payload["created_files"] == []
