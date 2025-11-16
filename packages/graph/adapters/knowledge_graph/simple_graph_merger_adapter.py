from __future__ import annotations

from typing import List

from application.use_cases.knowledge_graph.merge_knowledge_graphs_use_case import (
    GraphMergePort,
)
from domain.entities import KnowledgeGraph


class SimpleGraphMergerAdapter(GraphMergePort):
    """Adapter performing naive graph merging."""

    def __init__(self, repository):
        self.repository = repository

    def merge(
        self, *, target_kg_id: str, source_kg_ids: List[str], tenant_id: str
    ) -> KnowledgeGraph:
        target = self.repository.get_by_id(target_kg_id, tenant_id)
        if not target:
            raise ValueError("Target graph not found")
        for sid in source_kg_ids:
            src = self.repository.get_by_id(sid, tenant_id)
            if not src:
                continue
            target.node_count += src.node_count
            target.edge_count += src.edge_count
        self.repository.update(target)
        return target
