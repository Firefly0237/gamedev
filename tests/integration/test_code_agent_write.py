"""Code Agent 写文件协议测试。"""

from __future__ import annotations

import json
import os

import pytest

from graphs.orchestrator.workers._base import write_file


pytestmark = pytest.mark.integration


class TestCodeAgentWriteTool:
    def test_write_file_tool_returns_structured_success(
        self,
        mcp_initialized,
        test_project_path,
        cleanup_generated_files,
    ):
        _ = mcp_initialized
        rel_path = "Assets/Scripts/Data/CodeAgentWriteToolTest.cs"
        cleanup_generated_files.append(rel_path)

        raw = write_file.invoke(
            {
                "path": rel_path,
                "content": (
                    "namespace MyGame.Data\n"
                    "{\n"
                    "    public class CodeAgentWriteToolTest\n"
                    "    {\n"
                    "        public int value;\n"
                    "    }\n"
                    "}\n"
                ),
            }
        )
        result = json.loads(raw)

        assert result["status"] == "success"
        assert result["data"]["path"] == rel_path
        assert os.path.isfile(os.path.join(test_project_path, rel_path))
