"""Orchestrator worker 结果解析测试。"""

from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from graphs.orchestrator.result_parser import latest_worker_payload


pytestmark = pytest.mark.unit


class TestOrchestratorResultParser:
    def test_latest_worker_payload_uses_worker_json_without_tool_messages(self):
        messages = [
            ToolMessage(content="成功写入 Assets/Scripts/Foo.cs", tool_call_id="call_1"),
            AIMessage(
                content=json.dumps(
                    {
                        "worker": "code_agent",
                        "status": "success",
                        "summary": "创建 Foo.cs",
                        "created_files": ["Assets/Scripts/Foo.cs"],
                        "error_code": "",
                        "error_details": "",
                    },
                    ensure_ascii=False,
                ),
                name="code_agent",
            ),
        ]

        payload = latest_worker_payload(messages, {"code_agent"})

        assert payload is not None
        assert payload.created_files == ["Assets/Scripts/Foo.cs"]

    def test_latest_worker_payload_ignores_handoff_back_messages(self):
        messages = [
            AIMessage(
                content=json.dumps(
                    {
                        "worker": "code_agent",
                        "status": "success",
                        "summary": "创建 Foo.cs",
                        "created_files": ["Assets/Scripts/Foo.cs"],
                        "error_code": "",
                        "error_details": "",
                    },
                    ensure_ascii=False,
                ),
                name="code_agent",
            ),
            AIMessage(
                content="transferring back",
                name="code_agent",
                response_metadata={"__is_handoff_back": True},
            ),
        ]

        payload = latest_worker_payload(messages, {"code_agent"})

        assert payload is not None
        assert payload.created_files == ["Assets/Scripts/Foo.cs"]
