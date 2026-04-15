"""MCP 客户端集成测试。"""

import os

import pytest

from mcp_tools.mcp_client import call_mcp_tool, get_all_mcp_tools, get_mcp_status


pytestmark = pytest.mark.integration


class TestMCPClient:
    def test_status_contains_core_servers(self, mcp_initialized):
        _ = mcp_initialized
        status = get_mcp_status()
        assert status["fs"] is True
        assert status["git"] is True
        assert status["gamedev"] is True

    def test_tools_registered(self, mcp_initialized):
        _ = mcp_initialized
        tools = get_all_mcp_tools()
        assert "read_file" in tools
        assert "git_status" in tools
        assert "validate_all_configs" in tools

    def test_read_project_version(self, mcp_initialized, test_project_path):
        _ = mcp_initialized
        text = call_mcp_tool(
            "read_file",
            {"path": os.path.join(test_project_path, "ProjectSettings", "ProjectVersion.txt")},
        )
        assert "m_EditorVersion" in text
