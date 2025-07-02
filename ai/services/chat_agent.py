import os
from typing import List, Dict

from .llm_client import call_llm


class ChatAgent:
    """Simple in-memory chat agent using the configured LLM."""

    def __init__(self):
        self.history: List[Dict[str, str]] = []
        self.system_prompt = os.environ.get(
            "AGENT_SYSTEM",
            "Eres un asistente que responde sobre Ferrum y su grafo.yaml",
        )

    def chat(self, messages: List[Dict[str, str]], model: str | None = None) -> str:
        """Chat with memory of previous turns."""
        self.history.extend(messages)
        prompt = "\n".join(
            [h["content"] for h in self.history if h.get("role") == "user"]
        )
        reply = call_llm(prompt, self.system_prompt, model)
        self.history.append({"role": "assistant", "content": reply})
        return reply
