"""WorkerSpec 契约测试。"""

import pytest

from graphs.orchestrator.workers import ALL_SPECS


pytestmark = pytest.mark.unit


class TestWorkerSpec:
    def test_worker_names_are_unique(self):
        names = [spec.name for spec in ALL_SPECS]
        assert len(names) == len(set(names))

    def test_disabled_workers_do_not_expose_tools(self):
        for spec in ALL_SPECS:
            if not spec.enabled:
                assert spec.tools == []

    def test_code_agent_has_write_capability(self):
        code_spec = next(spec for spec in ALL_SPECS if spec.name == "code_agent")
        assert "write_file" in code_spec.tools
        assert code_spec.enabled is True
