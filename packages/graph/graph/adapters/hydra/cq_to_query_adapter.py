"""Adapters translating competency questions into backend queries."""

from __future__ import annotations

from typing import Dict

from application.ports.hydra import CQToQueryPort


class Neo4jCQToQueryAdapter(CQToQueryPort):
    """Map competency questions to Cypher queries for Neo4j."""

    def __init__(self, mapping: Dict[str, str]):
        self.mapping = mapping

    def to_query(self, *, question: str) -> str:
        return self.mapping.get(question, "")


class SparqlCQToQueryAdapter(CQToQueryPort):
    """Map competency questions to SPARQL queries."""

    def __init__(self, mapping: Dict[str, str]):
        self.mapping = mapping

    def to_query(self, *, question: str) -> str:
        return self.mapping.get(question, "")


__all__ = [
    "Neo4jCQToQueryAdapter",
    "SparqlCQToQueryAdapter",
]
