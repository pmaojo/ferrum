from __future__ import annotations

import json
from typing import Any

from application.ports.base import GraphExportPort


class SimpleGraphExportAdapter(GraphExportPort):
    """Minimal implementation of ``GraphExportPort`` for testing."""

    def __init__(self, repository):
        self.repository = repository

    def export_to_rdf(
        self, *, kg_id: str, tenant_id: str, format: str = "turtle"
    ) -> str:
        kg = self.repository.get_by_id(kg_id, tenant_id)
        return f"# RDF({format}) export for {kg.name}" if kg else ""

    def export_to_owl(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        ontology_version_id: str,
        format: str = "manchester",
    ) -> str:
        kg = self.repository.get_by_id(kg_id, tenant_id)
        return (
            f"# OWL({format}) export for {kg.name} v{ontology_version_id}" if kg else ""
        )

    def export_to_json(
        self, *, kg_id: str, tenant_id: str, include_metadata: bool = True
    ) -> str:
        kg = self.repository.get_by_id(kg_id, tenant_id)
        data: Any = (
            {
                "id": kg.id,
                "name": kg.name,
                "node_count": kg.node_count,
                "edge_count": kg.edge_count,
            }
            if kg
            else {}
        )
        return json.dumps(data)

    def export_to_cypher(self, *, kg_id: str, tenant_id: str) -> str:
        kg = self.repository.get_by_id(kg_id, tenant_id)
        return f"// Cypher export for {kg.name}" if kg else ""
