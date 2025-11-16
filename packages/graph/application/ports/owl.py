from abc import abstractmethod
from typing import Any, Dict, List, Optional, Protocol


class OwlAxiomGeneratorPort(Protocol):
    """Port for generating OWL axioms from natural language text."""

    @abstractmethod
    def generate_axioms(
        self,
        *,
        text: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Generate OWL axioms in Manchester syntax from text."""
        ...


__all__ = ["OwlAxiomGeneratorPort"]
