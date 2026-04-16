"""Orchestrator 的集成测试(mock planner + fake supervisor graph)。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from context.loader import load_skill
from graphs.orchestrator import resume_orchestrator, run_orchestrator
from tests.fixtures.mock_responses import subtask_plan_simple


pytestmark = pytest.mark.integration


class _FakeGraph:
    def __init__(self, test_project_path: str, responses: list[dict]):
        self.test_project_path = test_project_path
        self.responses = list(responses)
        self.calls: list[tuple[dict, dict]] = []

    def invoke(self, inputs: dict, config: dict | None = None):
        self.calls.append((inputs, config or {}))
        user_text = inputs["messages"][0].content
        payload = self.responses.pop(0)

        if "TestDataMock.cs" in user_text:
            file_path = Path(self.test_project_path) / "Assets" / "Scripts" / "Data" / "TestDataMock.cs"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(
                (
                    "namespace MyGame.Data\n"
                    "{\n"
                    "    public class TestDataMock\n"
                    "    {\n"
                    "        public string id;\n"
                    "        public string name;\n"
                    "    }\n"
                    "}\n"
                ),
                encoding="utf-8",
            )

        if "TestConfigMock.json" in user_text:
            file_path = Path(self.test_project_path) / "Assets" / "Resources" / "Configs" / "TestConfigMock.json"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(
                json.dumps([{"id": 1, "name": "A"}], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        return {"messages": [AIMessage(content=json.dumps(payload, ensure_ascii=False), name=payload["worker"])]}


class TestOrchestratorWithMockGraph:
    def test_plan_gate_returns_awaiting_approval(self, scanned_context, mock_llm):
        mock_llm.set_responses([subtask_plan_simple()], task_type="plan")
        skill = load_skill("generate_system")

        result = run_orchestrator("做一个 mock 系统", skill, None, scanned_context)

        assert result["status"] == "awaiting_approval"
        assert result["route"] == "orchestrator"
        assert len(result["actions"]) == 2
        assert result["actions"][0]["step_id"] == 1

    def test_two_file_generation_flow(
        self,
        scanned_context,
        mock_llm,
        test_project_path,
        cleanup_generated_files,
        monkeypatch,
    ):
        mock_llm.set_responses([subtask_plan_simple()], task_type="plan")
        fake_graph = _FakeGraph(
            test_project_path,
            responses=[
                {
                    "worker": "code_agent",
                    "status": "success",
                    "summary": "创建 TestDataMock.cs",
                    "created_files": ["Assets/Scripts/Data/TestDataMock.cs"],
                    "error_code": "",
                    "error_details": "",
                },
                {
                    "worker": "code_agent",
                    "status": "success",
                    "summary": "创建 TestConfigMock.json",
                    "created_files": ["Assets/Resources/Configs/TestConfigMock.json"],
                    "error_code": "",
                    "error_details": "",
                },
            ],
        )
        monkeypatch.setattr("graphs.orchestrator.get_graph", lambda: fake_graph)
        verify_calls = []

        def fake_run_verifier(files, project_context, skill_id):
            verify_calls.append((tuple(files), skill_id))
            return {
                "performed": True,
                "passed": True,
                "details": [{"type": "syntax", "passed": True, "message": "all good"}],
            }

        monkeypatch.setattr(
            "graphs.orchestrator.run_verifier",
            fake_run_verifier,
        )

        skill = load_skill("generate_system")
        handle = run_orchestrator("做一个 mock 系统", skill, None, scanned_context)
        result = resume_orchestrator(handle, approved=True)

        for rel_path in result["output_files"]:
            cleanup_generated_files.append(rel_path)

        assert result["status"] == "success"
        assert result["route"] == "orchestrator"
        assert "Assets/Scripts/Data/TestDataMock.cs" in result["output_files"]
        assert "Assets/Resources/Configs/TestConfigMock.json" in result["output_files"]
        assert result["verification"]["performed"] is True
        assert result["model_usage"]
        assert len(verify_calls) == 1
        assert fake_graph.calls

    def test_worker_failure_stops_execution(self, scanned_context, mock_llm, monkeypatch):
        mock_llm.set_responses([subtask_plan_simple()], task_type="plan")
        fake_graph = _FakeGraph(
            "",
            responses=[
                {
                    "worker": "art_agent",
                    "status": "failed",
                    "summary": "art_agent 当前尚未实装",
                    "created_files": [],
                    "error_code": "NOT_IMPLEMENTED",
                    "error_details": "stub",
                }
            ],
        )
        monkeypatch.setattr("graphs.orchestrator.get_graph", lambda: fake_graph)

        skill = load_skill("generate_system")
        handle = run_orchestrator("做一个 mock 系统", skill, None, scanned_context)
        result = resume_orchestrator(handle, approved=True)

        assert result["status"] in ("failed", "partial")
        assert "NOT_IMPLEMENTED" in result["error"]
