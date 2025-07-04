from typing import Protocol, List, Dict

class ChatHistory(Protocol):
    """Protocol for chat conversation history."""

    def append(self, message: Dict[str, str]) -> None:
        """Store a single chat message."""

    def get_user_messages(self) -> List[str]:
        """Return all user message contents in order."""


class InMemoryHistory:
    """Simple in-memory implementation of ChatHistory."""

    def __init__(self) -> None:
        self._messages: List[Dict[str, str]] = []

    def append(self, message: Dict[str, str]) -> None:
        self._messages.append(message)

    def get_user_messages(self) -> List[str]:
        return [m["content"] for m in self._messages if m.get("role") == "user"]
