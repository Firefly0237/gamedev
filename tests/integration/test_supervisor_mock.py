"""Supervisor 的集成测试(mock LLM + 真实文件落盘/验证)。"""

from __future__ import annotations

import json
import os

import pytest

from context.loader import load_skill
from graphs.safety import safe_write_file
from graphs.supervisor import run_supervisor
from tests.fixtures.mock_responses import subtask_plan_simple


pytestmark = pytest.mark.integration


def _fake_success_result(summary: str, output_files: list[str] | None = None, steps: int = 1) -> dict:
    return {
        "status": "success",
        "route": "agent_loop",
        "display": summary,
        "summary": summary,
        "output_files": output_files or [],
        "actions": [],
        "steps": steps,
        "verification": {"performed": False, "passed": False, "details": []},
        "tokens": 100,
        "duration": 0.1,
        "error": "",
        "task_id": None,
    }


class TestSupervisorWithMockLLM:
    def test_two_file_generation_flow(self, mcp_initialized, scanned_context, mock_llm, test_project_path, cleanup_generated_files, monkeypatch):
        _ = mcp_initialized
        mock_llm.set_responses([subtask_plan_simple()])

        def fake_run_agent_loop(user_input, skill=None, project_context=None, **kwargs):
            if "TestDataMock.cs" in user_input:
                rel_path = "Assets/Scripts/Data/TestDataMock.cs"
                content = (
                    "namespace MyGame.Data\n"
                    "{\n"
                    "    public class TestDataMock\n"
                    "    {\n"
                    "        public string id;\n"
                    "        public string name;\n"
                    "    }\n"
                    "}\n"
                )
                write = safe_write_file(rel_path, content, test_project_path)
                assert write["success"] is True
                return _fake_success_result("created TestDataMock.cs", [rel_path], steps=2)

            if "TestConfigMock.json" in user_input:
                rel_path = "Assets/Resources/Configs/TestConfigMock.json"
                content = json.dumps(
                    [
                        {"id": 1, "name": "A"},
                        {"id": 2, "name": "B"},
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
                write = safe_write_file(rel_path, content, test_project_path)
                assert write["success"] is True
                return _fake_success_result("created TestConfigMock.json", [rel_path], steps=2)

            raise AssertionError(f"unexpected subtask input: {user_input}")

        monkeypatch.setattr("graphs.supervisor.run_agent_loop", fake_run_agent_loop)

        skill = load_skill("generate_system")
        result = run_supervisor("做一个 mock 系统", skill, None, scanned_context)

        for rel_path in result["output_files"]:
            cleanup_generated_files.append(rel_path)

        assert result["status"] == "success"
        assert result["route"] == "supervisor"
        assert "Assets/Scripts/Data/TestDataMock.cs" in result["output_files"]
        assert "Assets/Resources/Configs/TestConfigMock.json" in result["output_files"]
        assert result["verification"]["performed"] is True
        assert result["verification"]["passed"] is True

    def test_missing_target_triggers_retry(self, mcp_initialized, scanned_context, mock_llm, test_project_path, cleanup_generated_files, monkeypatch):
        _ = mcp_initialized
        mock_llm.set_responses([subtask_plan_simple()])
        state = {"config_attempts": 0}

        def fake_run_agent_loop(user_input, skill=None, project_context=None, **kwargs):
            if "TestDataMock.cs" in user_input:
                rel_path = "Assets/Scripts/Data/TestDataMock.cs"
                content = (
                    "namespace MyGame.Data\n"
                    "{\n"
                    "    public class TestDataMock\n"
                    "    {\n"
                    "        public string id;\n"
                    "        public string name;\n"
                    "    }\n"
                    "}\n"
                )
                safe_write_file(rel_path, content, test_project_path)
                return _fake_success_result("created TestDataMock.cs", [rel_path], steps=2)

            if "TestConfigMock.json" in user_input and "紧急补写任务" not in user_input:
                state["config_attempts"] += 1
                return _fake_success_result("pretend config created", [], steps=1)

            if "紧急补写任务" in user_input and "TestConfigMock.json" in user_input:
                rel_path = "Assets/Resources/Configs/TestConfigMock.json"
                content = json.dumps([{"id": 1, "name": "Retry"}], ensure_ascii=False, indent=2)
                safe_write_file(rel_path, content, test_project_path)
                return _fake_success_result("retried config create", [rel_path], steps=1)

            raise AssertionError(f"unexpected subtask input: {user_input}")

        monkeypatch.setattr("graphs.supervisor.run_agent_loop", fake_run_agent_loop)

        skill = load_skill("generate_system")
        result = run_supervisor("做一个 mock 系统", skill, None, scanned_context)

        for rel_path in result["output_files"]:
            cleanup_generated_files.append(rel_path)

        assert state["config_attempts"] == 1
        assert result["status"] == "success"
        assert "Assets/Resources/Configs/TestConfigMock.json" in result["output_files"]
        assert os.path.isfile(os.path.join(test_project_path, "Assets/Resources/Configs/TestConfigMock.json"))
