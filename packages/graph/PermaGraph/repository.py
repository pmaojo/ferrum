from __future__ import annotations

"""Repository abstractions and implementations for the PermaGraph."""

from dataclasses import asdict
import json
import os
from typing import Dict, List, Protocol

from .domain import (
    ClarifyingQuestion,
    Edge,
    FeatureRequest,
    Persona,
    ScopeDocument,
)


class GraphRepository(Protocol):
    """Protocol defining persistence operations for graph artifacts."""

    def add_feature_request(self, feature_request: FeatureRequest) -> None:
        ...

    def add_scope_document(self, scope_document: ScopeDocument) -> None:
        ...

    def add_persona(self, persona: Persona) -> None:
        ...

    def add_clarifying_question(self, question: ClarifyingQuestion) -> None:
        ...

    def add_edge(self, edge: Edge) -> None:
        ...

    def get_edges(self) -> List[Edge]:
        ...


class InMemoryGraphRepository(GraphRepository):
    """In-memory repository used for testing."""

    def __init__(self) -> None:
        self.feature_requests: Dict[str, FeatureRequest] = {}
        self.scope_documents: Dict[str, ScopeDocument] = {}
        self.personas: Dict[str, Persona] = {}
        self.clarifying_questions: Dict[str, ClarifyingQuestion] = {}
        self.edges: List[Edge] = []

    def add_feature_request(self, feature_request: FeatureRequest) -> None:
        self.feature_requests[feature_request.id] = feature_request

    def add_scope_document(self, scope_document: ScopeDocument) -> None:
        self.scope_documents[scope_document.id] = scope_document

    def add_persona(self, persona: Persona) -> None:
        self.personas[persona.id] = persona

    def add_clarifying_question(self, question: ClarifyingQuestion) -> None:
        self.clarifying_questions[question.id] = question

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def get_edges(self) -> List[Edge]:
        return list(self.edges)


class JsonFileGraphRepository(GraphRepository):
    """Simple file-based repository storing graph data as JSON."""

    def __init__(self, path: str) -> None:
        self._path = path
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = {
                "feature_requests": {},
                "scope_documents": {},
                "personas": {},
                "clarifying_questions": {},
                "edges": [],
            }
            self._commit()

    def _commit(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f)

    def add_feature_request(self, feature_request: FeatureRequest) -> None:
        self._data["feature_requests"][feature_request.id] = asdict(feature_request)
        self._commit()

    def add_scope_document(self, scope_document: ScopeDocument) -> None:
        self._data["scope_documents"][scope_document.id] = asdict(scope_document)
        self._commit()

    def add_persona(self, persona: Persona) -> None:
        self._data["personas"][persona.id] = asdict(persona)
        self._commit()

    def add_clarifying_question(self, question: ClarifyingQuestion) -> None:
        self._data["clarifying_questions"][question.id] = asdict(question)
        self._commit()

    def add_edge(self, edge: Edge) -> None:
        self._data["edges"].append(asdict(edge))
        self._commit()

    def get_edges(self) -> List[Edge]:
        return [Edge(**edge) for edge in self._data.get("edges", [])]
