"""verify_files 的集成测试。"""

from __future__ import annotations

import os

import pytest

from graphs.verify import verify_files


pytestmark = pytest.mark.integration


class TestVerifyFilesOffMode:
    def test_off_mode_returns_skip(self, mcp_initialized, test_project_path):
        _ = mcp_initialized
        result = verify_files(
            files=["Assets/Scripts/Player/PlayerController.cs"],
            project_context={"project_path": test_project_path},
            mode="off",
        )
        assert result["performed"] is False
        assert result["passed"] is True


class TestVerifyFilesSyntaxMode:
    def test_good_cs_file(self, mcp_initialized, test_project_path, cleanup_generated_files):
        _ = mcp_initialized
        rel_path = "Assets/Scripts/GoodVerify.cs"
        full = os.path.join(test_project_path, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as file_obj:
            file_obj.write("using UnityEngine;\npublic class GoodVerify : MonoBehaviour { void Start() { } }")
        cleanup_generated_files.append(rel_path)

        result = verify_files(
            files=[rel_path],
            project_context={"project_path": test_project_path},
            mode="syntax",
        )
        assert result["performed"] is True
        assert result["passed"] is True

    def test_bad_cs_file(self, mcp_initialized, test_project_path, cleanup_generated_files):
        _ = mcp_initialized
        rel_path = "Assets/Scripts/BadVerify.cs"
        full = os.path.join(test_project_path, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as file_obj:
            file_obj.write("public class Bad : MonoBehaviour { void X() {")
        cleanup_generated_files.append(rel_path)

        result = verify_files(
            files=[rel_path],
            project_context={"project_path": test_project_path},
            mode="syntax",
        )
        assert result["performed"] is True
        assert result["passed"] is False

    def test_nunit_skill_detects_missing_attribute(self, mcp_initialized, test_project_path, cleanup_generated_files):
        _ = mcp_initialized
        rel_path = "Assets/Tests/Editor/BadNUnitTests.cs"
        full = os.path.join(test_project_path, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as file_obj:
            file_obj.write("using UnityEngine;\npublic class BadNUnitTests { void X() { } }")
        cleanup_generated_files.append(rel_path)

        result = verify_files(
            files=[rel_path],
            project_context={"project_path": test_project_path},
            mode="syntax",
            skill_id="generate_test",
        )
        assert result["passed"] is False
        fail_msgs = " ".join(detail["message"] for detail in result["details"] if not detail.get("passed"))
        assert "NUnit" in fail_msgs or "[Test]" in fail_msgs
