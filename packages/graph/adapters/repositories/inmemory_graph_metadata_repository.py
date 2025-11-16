"""In-memory repository for graph metadata, useful for testing."""

from typing import Any, Dict, Tuple

from application.use_cases.knowledge_graph.metadata_repository import (
    GraphMetadataRepositoryPort,
)


class InMemoryGraphMetadataRepository(GraphMetadataRepositoryPort):
    """Simple in-memory storage of knowledge graph metadata keyed by tenant and graph."""

    def __init__(self) -> None:
        self._store: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def save_description(self, kg_id: str, tenant_id: str, description: str) -> None:
        metadata = self._store.setdefault((tenant_id, kg_id), {})
        metadata["description"] = description

    def get_metadata(self, kg_id: str, tenant_id: str) -> Dict[str, Any]:
        return dict(self._store.get((tenant_id, kg_id), {}))
