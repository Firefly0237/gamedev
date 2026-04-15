"""任务卡片基础渲染函数测试。"""

import pytest

import pages._task_card as task_card


pytestmark = pytest.mark.unit


class _DummyTarget:
    pass


class TestTaskCardHelpers:
    def test_status_icon(self):
        assert task_card._status_icon("success") == "✅"
        assert task_card._status_icon("partial") == "⚠️"
        assert task_card._status_icon("failed") == "❌"

    def test_route_badge(self):
        assert "确定性" in task_card._route_badge("deterministic")
        assert "Agent" in task_card._route_badge("agent_loop")
        assert "Supervisor" in task_card._route_badge("supervisor")

    def test_verification_badge(self):
        assert "未验证" in task_card._verification_badge({})
        assert "验证通过" in task_card._verification_badge({"performed": True, "passed": True})
        assert "未通过" in task_card._verification_badge({"performed": True, "passed": False})

    def test_get_route_stages(self):
        deterministic = task_card.get_route_stages("deterministic")
        supervisor = task_card.get_route_stages("supervisor")
        agent_loop = task_card.get_route_stages("agent_loop")
        assert len(deterministic) == 3
        assert len(supervisor) == 4
        assert len(agent_loop) == 4


class TestTaskCardDispatch:
    def test_failed_result_uses_simple_card(self, monkeypatch):
        called = []
        monkeypatch.setattr(task_card, "_render_simple_card", lambda result, target: called.append("simple"))
        monkeypatch.setattr(task_card, "_render_step_card", lambda result, target: called.append("step"))
        monkeypatch.setattr(task_card, "_render_content_card", lambda result, target: called.append("content"))

        task_card.render_task_card({"status": "failed", "route": "agent_loop", "output_files": [], "actions": []}, _DummyTarget())
        assert called == ["simple"]

    def test_supervisor_uses_step_card(self, monkeypatch):
        called = []
        monkeypatch.setattr(task_card, "_render_step_card", lambda result, target: called.append("step"))
        monkeypatch.setattr(task_card, "_render_content_card", lambda result, target: called.append("content"))

        task_card.render_task_card(
            {"status": "success", "route": "supervisor", "output_files": [], "actions": [{"step_id": 1}]},
            _DummyTarget(),
        )
        assert called == ["step"]

    def test_agent_loop_uses_content_card(self, monkeypatch):
        called = []
        monkeypatch.setattr(task_card, "_render_step_card", lambda result, target: called.append("step"))
        monkeypatch.setattr(task_card, "_render_content_card", lambda result, target: called.append("content"))

        task_card.render_task_card(
            {"status": "success", "route": "agent_loop", "output_files": [], "actions": [{"step_id": 1}]},
            _DummyTarget(),
        )
        assert called == ["content"]


class TestDeterministicActionRender:
    class FakeTarget:
        def __init__(self):
            self.markdowns = []
            self.captions = []

        def markdown(self, text):
            self.markdowns.append(text)

        def caption(self, text):
            self.captions.append(text)

    def test_config_modify_action(self):
        target = self.FakeTarget()
        task_card._render_single_deterministic_action(
            {"success": True, "file": "WeaponConfig.json", "field": "damage", "old": 100, "new": 150},
            target,
        )
        assert "damage" in target.markdowns[0]

    def test_config_batch_action(self):
        target = self.FakeTarget()
        task_card._render_single_deterministic_action(
            {"success": True, "match": "火焰剑", "field": "damage", "old": 100, "new": 110},
            target,
        )
        assert "火焰剑" in target.markdowns[0]

    def test_code_modify_action(self):
        target = self.FakeTarget()
        task_card._render_single_deterministic_action(
            {"success": True, "file": "PlayerController.cs", "search": "moveSpeed = 5f", "replace": "moveSpeed = 8f"},
            target,
        )
        assert "PlayerController.cs" in target.markdowns[0]

    def test_failed_action_shows_error(self):
        target = self.FakeTarget()
        task_card._render_single_deterministic_action(
            {"success": False, "match": "火焰剑", "field": "damage", "old": 100, "new": 110, "error": "bad write"},
            target,
        )
        assert target.captions
