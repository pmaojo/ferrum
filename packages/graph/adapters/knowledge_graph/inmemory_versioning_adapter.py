from __future__ import annotations

from datetime import datetime
from typing import Dict, List
from uuid import uuid4

from application.use_cases.knowledge_graph.version_knowledge_graph_use_case import (
    KnowledgeGraphVersionDTO,
    KnowledgeGraphVersioningPort,
)


class InMemoryVersioningAdapter(KnowledgeGraphVersioningPort):
    """In-memory implementation of graph versioning."""

    def __init__(self) -> None:
        self._store: Dict[str, List[KnowledgeGraphVersionDTO]] = {}

    def create_version(
        self, *, kg_id: str, tenant_id: str, parent_version_id: str | None
    ) -> KnowledgeGraphVersionDTO:
        version = KnowledgeGraphVersionDTO(
            version_id=str(uuid4()),
            kg_id=kg_id,
            parent_version_id=parent_version_id,
            created_at=datetime.utcnow().isoformat(),
        )
        self._store.setdefault((tenant_id + kg_id), []).append(version)
        return version

    def list_versions(
        self, *, kg_id: str, tenant_id: str
    ) -> List[KnowledgeGraphVersionDTO]:
        return list(self._store.get((tenant_id + kg_id), []))
