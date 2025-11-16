"""Ports for knowledge discovery services."""

from abc import abstractmethod
from typing import List, Protocol

from domain.entities import Triple
from domain.knowledge_discovery import Anomaly, Hypothesis, Pattern, ValidationResult


class TripleProviderPort(Protocol):
    """Retrieve triples for a knowledge graph."""

    @abstractmethod
    def get_triples(self, *, kg_id: str, tenant_id: str) -> List[Triple]: ...


class PatternMiningPort(Protocol):
    """Discover frequent patterns."""

    @abstractmethod
    def mine(self, *, triples: List[Triple], min_support: int = 2) -> List[Pattern]: ...


class OntologyEnrichmentPort(Protocol):
    """Suggest ontology enrichments."""

    @abstractmethod
    def suggest(
        self,
        *,
        triples: List[Triple],
        ontology_version_id: str,
        tenant_id: str,
    ) -> List[Hypothesis]: ...


class AnomalyDetectionPort(Protocol):
    """Detect anomalies in triples."""

    @abstractmethod
    def detect(
        self,
        *,
        triples: List[Triple],
        ontology_version_id: str,
        tenant_id: str,
    ) -> List[Anomaly]: ...


class HypothesisGenerationPort(Protocol):
    """Generate hypotheses from patterns."""

    @abstractmethod
    def generate(
        self,
        *,
        patterns: List[Pattern],
        triples: List[Triple],
    ) -> List[Hypothesis]: ...


class DiscoveryValidationPort(Protocol):
    """Validate generated hypotheses."""

    @abstractmethod
    def validate(
        self,
        *,
        hypotheses: List[Hypothesis],
        ontology_version_id: str,
        tenant_id: str,
    ) -> List[ValidationResult]: ...


class DiscoveryVisualizationPort(Protocol):
    """Visualize discovered knowledge."""

    @abstractmethod
    def visualize_patterns(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        patterns: List[Pattern],
    ) -> dict: ...

    @abstractmethod
    def visualize_hypotheses(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        hypotheses: List[Hypothesis],
    ) -> dict: ...


__all__ = [
    "TripleProviderPort",
    "PatternMiningPort",
    "OntologyEnrichmentPort",
    "AnomalyDetectionPort",
    "HypothesisGenerationPort",
    "DiscoveryValidationPort",
    "DiscoveryVisualizationPort",
]
