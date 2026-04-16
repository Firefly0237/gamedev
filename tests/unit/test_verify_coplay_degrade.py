"""Unity Coplay 降级路径测试。"""

from __future__ import annotations

import pytest

from graphs.verify import verify_files


pytestmark = pytest.mark.unit


class TestVerifyCoplayDegrade:
    def test_full_mode_skips_compile_when_coplay_unavailable(self, monkeypatch):
        monkeypatch.setattr(
            "graphs.verify.call_mcp_tool",
            lambda name, arguments: "using UnityEngine;\npublic class Foo : MonoBehaviour { void Start() { } }",
        )
        monkeypatch.setattr("graphs.verify.get_all_mcp_tools", lambda: [])
        monkeypatch.setattr(
            "graphs.verify.get_unity_status",
            lambda: {"provider": "coplay", "package_installed": False, "connected": False},
        )

        result = verify_files(
            files=["Assets/Scripts/Foo.cs"],
            project_context={"project_path": "F:/fake"},
            mode="full",
        )

        assert result["passed"] is True
        compile_detail = next(detail for detail in result["details"] if detail["type"] == "compile")
        assert compile_detail["skipped"] is True
        assert compile_detail["error_code"] == "ENGINE_UNAVAILABLE"

