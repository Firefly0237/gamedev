"""MCP 客户端集成测试。"""

import pytest

from mcp_tools.mcp_client import call_mcp_tool, get_all_mcp_tools, get_mcp_status, get_unity_status


pytestmark = pytest.mark.integration


class TestMCPClient:
    def test_status_contains_core_servers(self, mcp_initialized):
        _ = mcp_initialized
        status = get_mcp_status()
        assert status["fs"] is True
        assert status["git"] is True

    def test_tools_registered(self, mcp_initialized):
        _ = mcp_initialized
        tools = get_all_mcp_tools()
        assert "read_file" in tools
        assert "git_status" in tools

    def test_read_project_version(self, mcp_initialized, test_project_path):
        _ = mcp_initialized
        text = call_mcp_tool(
            "read_file",
            {"path": f"{test_project_path}/ProjectSettings/ProjectVersion.txt"},
        )
        assert "m_EditorVersion" in text

    def test_unity_status_reports_missing_coplay_package_for_fixture_project(self, mcp_initialized):
        _ = mcp_initialized
        unity_status = get_unity_status()
        assert unity_status["provider"] == "coplay"
        assert unity_status["package_installed"] is False
        assert unity_status["connected"] is False
