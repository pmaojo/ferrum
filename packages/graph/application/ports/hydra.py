"""Hydra-related application layer ports."""

from abc import abstractmethod
from typing import Dict, List, Optional, Protocol


class PersonaGeneratorPort(Protocol):
    """Generate user personas from a textual description."""

    @abstractmethod
    def generate_personas(
        self,
        *,
        description: str,
        tenant_id: str,
        num_personas: int = 3,
        opts: Optional[Dict[str, object]] = None,
    ) -> List[str]:
        """Return a list of personas for the given description."""


class ScopeGeneratorPort(Protocol):
    """Generate project scope documents from a description."""

    @abstractmethod
    def generate_scope_document(
        self,
        *,
        description: str,
        tenant_id: str,
        opts: Optional[Dict[str, object]] = None,
    ) -> str:
        """Return a scope document for the given description."""


class CompetencyQuestionPort(Protocol):
    """Generate competency questions from contextual information."""

    @abstractmethod
    def generate_competency_questions(
        self,
        *,
        context: str,
        tenant_id: str,
        num_questions: int = 10,
        opts: Optional[Dict[str, object]] = None,
    ) -> List[str]:
        """Return a list of competency questions for the given context."""


class CQToQueryPort(Protocol):
    """Translate competency questions into backend-specific queries."""

    @abstractmethod
    def to_query(self, *, question: str) -> str:
        """Return query string for the provided competency question."""


__all__ = [
    "PersonaGeneratorPort",
    "ScopeGeneratorPort",
    "CompetencyQuestionPort",
    "CQToQueryPort",
]
