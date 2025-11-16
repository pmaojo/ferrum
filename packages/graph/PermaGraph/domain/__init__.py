from __future__ import annotations

"""Simple graph domain models for feature requests and related artifacts."""

from dataclasses import dataclass
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - used for type hints only
    from ..repository import GraphRepository


@dataclass
class FeatureRequest:
    """Represents a raw feature request."""

    id: str
    description: str


@dataclass
class ScopeDocument:
    """Scope document generated from a feature request."""

    id: str
    content: str
    feature_request_id: str


@dataclass
class Persona:
    """Generated user persona."""

    id: str
    content: str
    feature_request_id: str


@dataclass
class ClarifyingQuestion:
    """Clarifying question produced by HyDRA."""

    id: str
    question: str
    feature_request_id: str


@dataclass
class Edge:
    """Directed edge between nodes."""

    source: str
    target: str
    type: str


@dataclass
class Graph:
    """Graph facade that delegates persistence to a repository."""

    repository: "GraphRepository"

    def add_feature_request(self, feature_request: FeatureRequest) -> None:
        self.repository.add_feature_request(feature_request)

    def add_scope_document(self, scope_document: ScopeDocument) -> None:
        self.repository.add_scope_document(scope_document)
        self.repository.add_edge(
            Edge(
                source=scope_document.feature_request_id,
                target=scope_document.id,
                type="has_scope",
            )
        )

    def add_persona(self, persona: Persona) -> None:
        self.repository.add_persona(persona)
        self.repository.add_edge(
            Edge(
                source=persona.feature_request_id,
                target=persona.id,
                type="has_persona",
            )
        )

    def add_clarifying_question(self, question: ClarifyingQuestion) -> None:
        self.repository.add_clarifying_question(question)
        self.repository.add_edge(
            Edge(
                source=question.feature_request_id,
                target=question.id,
                type="has_clarifying_question",
            )
        )

    @property
    def edges(self) -> List[Edge]:
        return self.repository.get_edges()


__all__ = [
    "FeatureRequest",
    "ScopeDocument",
    "Persona",
    "ClarifyingQuestion",
    "Edge",
    "Graph",
]
