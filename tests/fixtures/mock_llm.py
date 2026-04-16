"""Mock LLM 工厂。"""

from __future__ import annotations

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.runnables.base import Runnable


class FakeToolCall:
    """模拟 tool_calls 里的对象。"""

    def __init__(self, name: str, args: dict, id: str = "call_mock"):
        self.name = name
        self.args = args
        self.id = id

    def __getitem__(self, key):
        return {"name": self.name, "args": self.args, "id": self.id}[key]


class FakeLLMResponse(AIMessage):
    """模拟 AIMessage 返回值。"""

    def __init__(self, content: str = "", tool_calls: list | None = None):
        super().__init__(
            content=content,
            tool_calls=tool_calls or [],
            response_metadata={"token_usage": {"total_tokens": 100}},
        )


class MockLLM(Runnable):
    """可预设响应序列的简单假 LLM。"""

    def __init__(self, task_type: str = "generation"):
        self.task_type = task_type
        self._responses: list = []
        self._bound_tools: list = []
        self._invocations: list = []

    def bind_tools(self, tools, *args, **kwargs):
        self._bound_tools = tools
        return self

    def set_responses(self, responses: list):
        self._responses = list(responses)

    def invoke(self, messages: list[BaseMessage], *args, **kwargs) -> FakeLLMResponse:
        self._invocations.append(messages)

        if not self._responses:
            return FakeLLMResponse(content="")

        response = self._responses.pop(0)
        if isinstance(response, str):
            return FakeLLMResponse(content=response)
        if isinstance(response, FakeLLMResponse):
            return response
        if isinstance(response, dict):
            return FakeLLMResponse(
                content=response.get("content", ""),
                tool_calls=response.get("tool_calls", []),
            )
        return response

    def stream(self, messages: list[BaseMessage], *args, **kwargs):
        response = self.invoke(messages, *args, **kwargs)
        yield AIMessageChunk(
            content=response.content,
            tool_calls=getattr(response, "tool_calls", []),
            response_metadata=getattr(response, "response_metadata", {}),
        )


class MockLLMFactory:
    """统一的 mock LLM 入口。"""

    def __init__(self):
        self._llms: dict[str, MockLLM] = {}

    def get_llm(self, task_type: str = "generation") -> MockLLM:
        if task_type not in self._llms:
            self._llms[task_type] = MockLLM(task_type)
        return self._llms[task_type]

    def set_responses(self, responses: list, task_type: str = "generation"):
        self.get_llm(task_type).set_responses(responses)

    def get_invocations(self, task_type: str = "generation") -> list:
        return self.get_llm(task_type)._invocations
