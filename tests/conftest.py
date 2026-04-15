"""全局共享 fixtures。"""

from __future__ import annotations

import os
import sys
from dataclasses import asdict
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def project_root():
    """项目根目录绝对路径。"""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def test_project_path(project_root):
    """test_project 的绝对路径。"""
    from tests.fixtures.test_project_setup import ensure_test_project

    return ensure_test_project(project_root)


@pytest.fixture(scope="session")
def scanned_context(test_project_path):
    """扫描 test_project，一次 session 复用。"""
    from scanner.unity_scanner import UnityScanner

    scanner = UnityScanner(test_project_path)
    scanner.clear_cache()
    return asdict(scanner.scan())


@pytest.fixture(scope="session")
def mcp_initialized(test_project_path):
    """初始化 MCP(FileSystem + Git + GameDev)。"""
    from mcp_tools.mcp_client import init_mcp

    init_mcp(test_project_path)
    yield


@pytest.fixture
def cleanup_generated_files(test_project_path):
    """测试结束后清理测试生成文件。"""
    tracked: list[str] = []
    yield tracked

    for rel_path in tracked:
        full = os.path.join(test_project_path, rel_path)
        if os.path.exists(full):
            try:
                os.remove(full)
            except Exception:
                pass
        bak = full + ".bak"
        if os.path.exists(bak):
            try:
                os.remove(bak)
            except Exception:
                pass


@pytest.fixture
def mock_llm(monkeypatch):
    """返回可配置的 Mock LLM 工厂。"""
    from tests.fixtures.mock_llm import MockLLMFactory

    factory = MockLLMFactory()

    def _create_llm_mock(task_type="generation", temperature=None):
        return factory.get_llm(task_type)

    monkeypatch.setattr("agents.llm.create_llm", _create_llm_mock)
    monkeypatch.setattr("graphs.agent_loop.create_llm", _create_llm_mock, raising=False)
    monkeypatch.setattr("graphs.deterministic.create_llm", _create_llm_mock, raising=False)
    monkeypatch.setattr("graphs.supervisor.create_llm", _create_llm_mock, raising=False)
    return factory


def pytest_collection_modifyitems(config, items):
    """没设置 RUN_E2E=1 时默认跳过 e2e 测试。"""
    if os.environ.get("RUN_E2E") == "1":
        return

    skip_e2e = pytest.mark.skip(reason="e2e 测试默认跳过, 设置 RUN_E2E=1 启用")
    for item in items:
        if "tests/e2e/" in str(item.fspath).replace("\\", "/"):
            item.add_marker(skip_e2e)
