import os
from typing import List, Dict

from .llm_client import call_llm
from .history import ChatHistory, InMemoryHistory


class ChatAgent:
    """Simple chat agent using the configured LLM."""

    def __init__(self, history: ChatHistory | None = None) -> None:
        self.history = history or InMemoryHistory()
        self.system_prompt = os.environ.get(
            "AGENT_SYSTEM",
            "Eres un asistente que responde sobre Ferrum y su grafo.yaml",
        )

    def chat(self, messages: List[Dict[str, str]], model: str | None = None) -> str:
        """Chat with memory of previous turns."""
        for message in messages:
            self.history.append(message)
        prompt = "\n".join(self.history.get_user_messages())
        reply = call_llm(prompt, self.system_prompt, model)
        self.history.append({"role": "assistant", "content": reply})
        return reply
