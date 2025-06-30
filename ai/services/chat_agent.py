import os
from typing import List, Dict

from .llm_client import call_llm


class ChatAgent:
    """Simple in-memory chat agent using the configured LLM."""

    def __init__(self):
        self.history: List[Dict[str, str]] = []
        self.system_prompt = os.environ.get(
            "AGENT_SYSTEM",
            "Eres un asistente que responde sobre Ferrus y su grafo.yaml",
        )

    def chat(self, message: str, model: str | None = None) -> str:
        self.history.append({"role": "user", "content": message})
        # Combine history into a single prompt for simplicity
        prompt = "\n".join([h["content"] for h in self.history if h["role"] == "user"])
        reply = call_llm(prompt, self.system_prompt, model)
        self.history.append({"role": "assistant", "content": reply})
        return reply
