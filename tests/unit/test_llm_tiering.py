"""模型分层与降级链测试。"""

from __future__ import annotations

import sys
import types

import pytest

from agents import llm as llm_module


pytestmark = pytest.mark.unit


def _clear_env(monkeypatch):
    for key in (
        "DEEPSEEK_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "ENABLE_MODEL_TIERING",
    ):
        monkeypatch.delenv(key, raising=False)


class FakeChatOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeChatAnthropic:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class TestLLMTiering:
    def test_generation_prefers_anthropic_when_available(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")

        info = llm_module.resolve_task_model("generation")

        assert info.provider == "anthropic"
        assert info.model == "claude-haiku-4-5"
        assert info.task_type == "generation"

    def test_generation_falls_back_to_openai(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")

        info = llm_module.resolve_task_model("generation")

        assert info.provider == "openai"
        assert info.model == "gpt-5.4-mini"
        assert info.fallback_from == ("anthropic",)

    def test_generation_falls_back_to_deepseek(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek")

        info = llm_module.resolve_task_model("generation")

        assert info.provider == "deepseek"
        assert info.model == "deepseek-chat"
        assert info.fallback_from == ("anthropic", "openai")

    def test_disable_tiering_requires_deepseek(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("ENABLE_MODEL_TIERING", "0")

        with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
            llm_module.resolve_task_model("plan")

    def test_create_llm_attaches_runtime_info(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
        monkeypatch.setattr(llm_module, "ChatOpenAI", FakeChatOpenAI)
        monkeypatch.setitem(sys.modules, "langchain_anthropic", types.SimpleNamespace(ChatAnthropic=FakeChatAnthropic))

        llm = llm_module.create_llm("generation", temperature=0.3)
        info = llm_module.get_llm_runtime_info(llm)

        assert isinstance(llm, FakeChatAnthropic)
        assert llm.kwargs["model"] == "claude-haiku-4-5"
        assert llm.kwargs["temperature"] == 0.3
        assert info is not None
        assert info.provider == "anthropic"

    def test_plan_alias_normalizes_from_planning(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")

        info = llm_module.resolve_task_model("planning")

        assert info.task_type == "plan"
        assert info.model == "claude-sonnet-4-5"
