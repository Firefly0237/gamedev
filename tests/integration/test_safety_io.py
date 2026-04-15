"""safety 层的集成测试。"""

from __future__ import annotations

import os

import pytest

from graphs.safety import normalize_path, safe_write_file


pytestmark = pytest.mark.integration


class TestNormalizePath:
    def test_relative_path(self, test_project_path):
        result = normalize_path("Assets/Foo.cs", test_project_path)
        assert os.path.isabs(result)
        assert result.endswith(os.path.normpath("Assets/Foo.cs"))

    def test_absolute_path(self, test_project_path):
        abs_path = os.path.join(test_project_path, "Assets", "Foo.cs")
        result = normalize_path(abs_path, test_project_path)
        assert result == os.path.normpath(abs_path)

    def test_project_prefixed_relative_path(self, test_project_path):
        project_name = os.path.basename(test_project_path)
        result = normalize_path(f"{project_name}\\Assets\\Foo.cs", test_project_path)
        assert result.endswith(os.path.normpath("Assets\\Foo.cs"))


class TestSafeWriteFile:
    def test_write_new_file(self, mcp_initialized, test_project_path, cleanup_generated_files):
        _ = mcp_initialized
        rel_path = "Assets/Scripts/SafetyTest.txt"
        result = safe_write_file(rel_path, "hello world", test_project_path)
        cleanup_generated_files.append(rel_path)

        assert result["success"] is True
        assert result["is_new"] is True

    def test_write_existing_file_produces_diff(self, mcp_initialized, test_project_path, cleanup_generated_files):
        _ = mcp_initialized
        rel_path = "Assets/Scripts/SafetyDiff.txt"
        safe_write_file(rel_path, "line1\nline2\nline3", test_project_path)
        cleanup_generated_files.append(rel_path)

        result = safe_write_file(rel_path, "line1\nMODIFIED\nline3", test_project_path)
        assert result["success"] is True
        assert result["is_new"] is False
        assert len(result.get("diff", "")) > 0
