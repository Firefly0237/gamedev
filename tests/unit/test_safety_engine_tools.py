"""Safety 层 engine tool 降级测试。"""

from __future__ import annotations

import json

import pytest

from graphs.safety import execute_tool_safely


pytestmark = pytest.mark.unit


class TestSafetyEngineTools:
    def test_engine_compile_returns_structured_unavailable_error(self, monkeypatch):
        monkeypatch.setattr("mcp_tools.mcp_client.get_all_mcp_tools", lambda: [])

        payload = json.loads(execute_tool_safely("engine_compile", {"files": ["Assets/Scripts/Foo.cs"]}, "F:/fake"))

        assert payload["status"] == "error"
        assert payload["error_code"] == "ENGINE_UNAVAILABLE"
