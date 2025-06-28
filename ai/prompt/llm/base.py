from abc import ABC, abstractmethod

class LLMBackend(ABC):
    """Abstract base class for language model backends."""

    @abstractmethod
    def generate_yaml(self, prompt: str) -> str:
        """Generate YAML from a text prompt."""
        raise NotImplementedError
