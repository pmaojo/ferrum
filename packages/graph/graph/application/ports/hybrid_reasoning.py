from abc import abstractmethod
from typing import Any, Dict, List, Protocol

from domain.entities import Triple, ValidationReport


class OntologyLoaderPort(Protocol):
    """Port for loading OWL ontologies from various sources."""

    @abstractmethod
    def load(self, *, path: str) -> Any:
        """Load ontology from file path and return ontology object."""
        ...


class ConsistencyCheckerPort(Protocol):
    """Port for checking ontology consistency."""

    @abstractmethod
    def check(
        self, *, triples: List[Triple], ontology_version_id: str
    ) -> ValidationReport:
        """Validate triples for consistency against an ontology version."""
        ...


class ReasoningExplanationPort(Protocol):
    """Port for generating natural language explanations of reasoning."""

    @abstractmethod
    def explain(
        self, *, report: ValidationReport, llm_output: str, tenant_id: str
    ) -> str:
        """Produce explanation for reasoning result."""
        ...


class EntityLinkingPort(Protocol):
    """Port for linking text entities to ontology concepts."""

    @abstractmethod
    def link(self, *, text: str, ontology: Any, tenant_id: str) -> List[str]:
        """Return list of ontology IRIs mapped from text."""
        ...


class HybridReasoningPort(Protocol):
    """Port for combining LLM and OWL reasoning."""

    @abstractmethod
    def reason(
        self,
        *,
        question: str,
        triples: List[Triple],
        ontology_version_id: str,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Execute hybrid reasoning pipeline and return result."""
        ...


__all__ = [
    "OntologyLoaderPort",
    "ConsistencyCheckerPort",
    "ReasoningExplanationPort",
    "EntityLinkingPort",
    "HybridReasoningPort",
]
