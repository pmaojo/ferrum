"""Tests for :mod:`ai.services.chat_agent`.

This module patches missing third-party dependencies so the tests can run
in isolation without requiring those packages installed. It focuses on the
interaction between :class:`ChatAgent` and its history/LLM client.
"""

from types import ModuleType
import sys

# Provide a minimal ``yaml`` module if it's not installed. The production code
# imports ``yaml`` in ``llm_client`` but the tests don't rely on its features.
if "yaml" not in sys.modules:
    stub = ModuleType("yaml")
    stub.safe_load = lambda *_args, **_kwargs: {}
    sys.modules["yaml"] = stub

from ..services import chat_agent
from ..services.chat_agent import ChatAgent


class DummyHistory:
    """Minimal history to capture chat interactions."""

    def __init__(self) -> None:
        self.messages = []

    def append(self, message: dict) -> None:
        self.messages.append(message)

    def get_user_messages(self) -> list[str]:
        return [m["content"] for m in self.messages if m.get("role") == "user"]


def test_chat_appends_and_calls_llm(monkeypatch):
    history = DummyHistory()
    agent = ChatAgent(history=history)

    captured = {}

    def fake_call_llm(prompt: str, system: str, model: str | None = None) -> str:
        captured["args"] = (prompt, system, model)
        return "response"

    monkeypatch.setattr(chat_agent, "call_llm", fake_call_llm)

    messages = [
        {"role": "user", "content": "hi"},
        {"role": "user", "content": "there"},
    ]

    reply = agent.chat(messages, model="gpt-4")

    assert reply == "response"
    assert history.messages == messages + [{"role": "assistant", "content": "response"}]
    expected_prompt = "\n".join(["hi", "there"])
    assert captured["args"] == (expected_prompt, agent.system_prompt, "gpt-4")
