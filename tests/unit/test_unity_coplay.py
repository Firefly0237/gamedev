"""Coplay Unity 适配层测试。"""

from __future__ import annotations

import json

import pytest

from mcp_tools.unity_coplay import (
    detect_coplay_package,
    is_engine_tool_available,
    run_engine_compile,
    run_engine_tests,
)


pytestmark = pytest.mark.unit


class TestDetectCoplayPackage:
    def test_detect_coplay_package_from_manifest(self, tmp_path):
        (tmp_path / "Assets").mkdir()
        (tmp_path / "ProjectSettings").mkdir()
        (tmp_path / "Packages").mkdir()
        (tmp_path / "Packages" / "manifest.json").write_text(
            json.dumps({"dependencies": {"com.coplaydev.unity-mcp": "https://example.invalid"}}),
            encoding="utf-8",
        )

        status = detect_coplay_package(str(tmp_path))

        assert status["is_unity_project"] is True
        assert status["package_installed"] is True


class TestEngineAvailability:
    def test_engine_compile_requires_validate_and_console_tools(self):
        assert is_engine_tool_available("engine_compile", {"read_console"}) is False
        assert is_engine_tool_available("engine_compile", {"read_console", "validate_script"}) is True


class TestRunEngineCompile:
    def test_run_engine_compile_combines_validate_and_console_errors(self):
        def fake_call_tool(name, arguments):
            if name == "validate_script":
                return {
                    "success": True,
                    "data": {
                        "diagnostics": [
                            {
                                "severity": "error",
                                "line": 12,
                                "column": 5,
                                "code": "CS0246",
                                "message": "The type or namespace name 'Foo' could not be found",
                            }
                        ]
                    },
                }
            if name == "read_console":
                return {
                    "success": True,
                    "data": {
                        "items": [
                            {
                                "level": "error",
                                "message": "Assets/Scripts/Test.cs(12,5): error CS0246: The type or namespace name 'Foo' could not be found",
                            }
                        ]
                    },
                }
            raise AssertionError(name)

        result = run_engine_compile(fake_call_tool, ["Assets/Scripts/Test.cs"])

        assert result["success"] is False
        assert result["errors"]
        assert result["errors"][0]["file"] == "Assets/Scripts/Test.cs"


class TestRunEngineTests:
    def test_run_engine_tests_polls_until_complete(self, monkeypatch):
        calls = []
        monkeypatch.setattr("mcp_tools.unity_coplay.time.sleep", lambda _: None)

        def fake_call_tool(name, arguments):
            calls.append((name, arguments))
            if name == "run_tests":
                return {"success": True, "data": {"job_id": "job-1"}}
            if len(calls) == 2:
                return {"success": True, "data": {"status": "running"}}
            return {
                "success": True,
                "data": {
                    "status": "succeeded",
                    "result": {
                        "summary": {"passed": 3, "failed": 0, "skipped": 1},
                        "results": [],
                    },
                },
            }

        result = run_engine_tests(fake_call_tool, wait_timeout=5)

        assert result["passed"] == 3
        assert result["failed"] == 0
        assert any(name == "get_test_job" for name, _ in calls)
