"""Orchestrator 真实端到端测试。"""

from __future__ import annotations

import os

import pytest

from context.loader import load_skill
from graphs.orchestrator import resume_orchestrator, run_orchestrator


pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.timeout(180)]


class TestOrchestratorE2E:
    def test_two_file_system(self, mcp_initialized, scanned_context, test_project_path, cleanup_generated_files):
        _ = mcp_initialized
        skill = load_skill("generate_system")

        handle = run_orchestrator(
            "创建一个简单的测试成就系统,只需要两个文件: "
            "AchievementTestData.cs(含 id/name 字段) 和 "
            "AchievementTestConfig.json(含 2 个示例成就)",
            skill,
            None,
            scanned_context,
        )
        result = resume_orchestrator(handle, approved=True)

        assert result["status"] in ("success", "partial")

        for rel_path in result["output_files"]:
            full = os.path.join(test_project_path, rel_path)
            cleanup_generated_files.append(rel_path)
            assert os.path.isfile(full)

        assert result["verification"]["performed"] is True

    def test_orchestrator_result_structure(self, mcp_initialized, scanned_context, cleanup_generated_files):
        _ = mcp_initialized
        skill = load_skill("generate_system")

        handle = run_orchestrator(
            "创建一个 SupervisorStructTest.cs 测试类",
            skill,
            None,
            scanned_context,
        )
        result = resume_orchestrator(handle, approved=True)

        for file_path in result.get("output_files", []):
            cleanup_generated_files.append(file_path)

        assert "route" in result
        assert result["route"] == "orchestrator"
        assert "actions" in result
        assert "summary" in result
        assert "output_files" in result
        assert "verification" in result

        for action in result["actions"]:
            assert "step_id" in action or "description" in action
