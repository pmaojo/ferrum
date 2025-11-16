from __future__ import annotations

import abc
from typing import Any, Dict, Optional

from application.use_cases.create_knowledge_graph_use_case import (
    KnowledgeGraphRepositoryPort,
)
from application.use_cases.dto import SortDirection, SortParams
from application.use_cases.list_knowledge_graphs_use_case import (
    KnowledgeGraphFilterParams,
)
from domain.entities import KnowledgeGraph, ScientificDomain


class AbstractKnowledgeGraphRepository(KnowledgeGraphRepositoryPort, abc.ABC):
    """Shared logic for knowledge graph repositories."""

    SORT_FIELD_MAPPING = {
        "name": "name",
        "created_at": "created_at",
        "updated_at": "updated_at",
        "node_count": "node_count",
        "edge_count": "edge_count",
        "domain": "domain",
    }

    def _entity_to_dict(self, kg: KnowledgeGraph) -> Dict[str, Any]:
        return {
            "id": kg.id,
            "name": kg.name,
            "tenant_id": kg.tenant_id,
            "domain": (
                kg.domain.value
                if isinstance(kg.domain, ScientificDomain)
                else kg.domain
            ),
            "ontology_version_id": kg.ontology_version_id,
            "created_at": kg.created_at,
            "updated_at": kg.updated_at,
            "node_count": kg.node_count,
            "edge_count": kg.edge_count,
            "is_public": kg.is_public,
        }

    def _dict_to_entity(self, data: Dict[str, Any]) -> KnowledgeGraph:
        return KnowledgeGraph(
            id=data["id"],
            name=data["name"],
            tenant_id=data["tenant_id"],
            domain=(
                data["domain"]
                if isinstance(data["domain"], ScientificDomain)
                else ScientificDomain(data["domain"])
            ),
            ontology_version_id=data["ontology_version_id"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            node_count=data["node_count"],
            edge_count=data["edge_count"],
            is_public=data["is_public"],
        )

    def _extract_filters(
        self, filters: Optional[KnowledgeGraphFilterParams]
    ) -> Dict[str, Any]:
        if not filters:
            return {}

        mapping: Dict[str, Any] = {}
        if filters.domain is not None:
            mapping["domain"] = (
                filters.domain.value
                if isinstance(filters.domain, ScientificDomain)
                else filters.domain
            )
        if filters.is_public is not None:
            mapping["is_public"] = filters.is_public
        if filters.name_contains is not None:
            mapping["name_contains"] = filters.name_contains
        if filters.min_node_count is not None:
            mapping["min_node_count"] = filters.min_node_count
        if filters.max_node_count is not None:
            mapping["max_node_count"] = filters.max_node_count
        if filters.min_edge_count is not None:
            mapping["min_edge_count"] = filters.min_edge_count
        if filters.max_edge_count is not None:
            mapping["max_edge_count"] = filters.max_edge_count
        if filters.created_after is not None:
            mapping["created_after"] = filters.created_after
        if filters.created_before is not None:
            mapping["created_before"] = filters.created_before
        if filters.updated_after is not None:
            mapping["updated_after"] = filters.updated_after
        if filters.updated_before is not None:
            mapping["updated_before"] = filters.updated_before
        return mapping

    def _resolve_sort(self, sort: Optional[SortParams]) -> Dict[str, Any]:
        field = "created_at"
        direction = SortDirection.DESC
        if sort:
            field = self.SORT_FIELD_MAPPING.get(sort.sort_by, "created_at")
            direction = sort.direction
        return {"field": field, "direction": direction}
