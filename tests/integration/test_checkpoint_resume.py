"""Checkpoint 接线测试。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from langchain_core.messages import HumanMessage

from graphs.orchestrator.supervisor import build_supervisor_graph


pytestmark = pytest.mark.integration


class _FakeCompiledGraph:
    store: dict[str, list] = {}

    def invoke(self, inputs: dict, config: dict | None = None):
        thread_id = (config or {}).get("configurable", {}).get("thread_id", "default")
        self.store[thread_id] = list(inputs.get("messages", []))
        return {"messages": self.store[thread_id]}

    def get_state(self, config: dict):
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        return SimpleNamespace(values={"messages": self.store.get(thread_id, [])})


class _FakeSupervisorBuilder:
    def __init__(self):
        self.received_checkpointers = []

    def __call__(self, *args, **kwargs):
        return self

    def compile(self, checkpointer=None):
        self.received_checkpointers.append(checkpointer)
        return _FakeCompiledGraph()


class TestCheckpointResume:
    def test_build_supervisor_graph_preserves_thread_state_across_rebuild(self, monkeypatch):
        fake_builder = _FakeSupervisorBuilder()
        monkeypatch.setattr("graphs.orchestrator.supervisor.create_supervisor", fake_builder)
        monkeypatch.setattr("graphs.orchestrator.supervisor.create_llm", lambda *args, **kwargs: object())
        monkeypatch.setattr("graphs.orchestrator.supervisor.get_all_agents", lambda: [])

        saver = object()
        graph1 = build_supervisor_graph(saver)
        config = {"configurable": {"thread_id": "checkpoint-thread-1"}}
        graph1.invoke({"messages": [HumanMessage(content="step 1")]}, config=config)

        graph2 = build_supervisor_graph(saver)
        state = graph2.get_state(config).values

        assert fake_builder.received_checkpointers == [saver, saver]
        assert state["messages"]
