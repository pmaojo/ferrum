from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, NamedTuple, Optional

from ..exceptions import ValidationError
from .enums import GraphStreamEventType, ScientificDomain


class Triple(NamedTuple):
    """Knowledge graph triple with tenant isolation."""

    subject: str
    predicate: str
    object: str
    tenant_id: str


class ValidationReport(NamedTuple):
    """Ontology validation results with tenant and version context."""

    is_consistent: bool
    unsat_classes: List[str]
    repair_suggestions: List[str]
    tenant_id: str
    ontology_version_id: str
    explanation: Optional[str] = None


class GraphStreamEvent(NamedTuple):
    """Real-time graph update event with tenant isolation."""

    event_type: GraphStreamEventType
    data: Dict[str, Any]
    timestamp: datetime
    kg_id: str
    tenant_id: str


class Community(NamedTuple):
    """Graph community for clustering and visualization."""

    id: str
    centroid_embedding: List[float]
    node_ids: List[str]
    size: int
    tenant_id: str


@dataclass
class KnowledgeGraph:
    """Knowledge graph entity with multi-tenant support."""

    id: str
    name: str
    tenant_id: str
    domain: ScientificDomain
    ontology_version_id: str
    created_at: datetime
    updated_at: datetime
    node_count: int
    edge_count: int
    is_public: bool = False

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(
                message="Knowledge graph ID must be a non-empty string", param="id"
            )

        if not self.name or not isinstance(self.name, str):
            raise ValidationError(
                message="Knowledge graph name must be a non-empty string", param="name"
            )

        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValidationError(
                message="Tenant ID must be a non-empty string", param="tenant_id"
            )

        if not isinstance(self.domain, ScientificDomain):
            raise ValidationError(message="Domain must be a valid ScientificDomain", param="domain")

        if not self.ontology_version_id or not isinstance(self.ontology_version_id, str):
            raise ValidationError(
                message="Ontology version ID must be a non-empty string",
                param="ontology_version_id",
            )

        if not isinstance(self.created_at, datetime):
            raise ValidationError(message="Created at must be a datetime object", param="created_at")

        if not isinstance(self.updated_at, datetime):
            raise ValidationError(message="Updated at must be a datetime object", param="updated_at")

        if not isinstance(self.node_count, int) or self.node_count < 0:
            raise ValidationError(message="Node count must be a non-negative integer", param="node_count")

        if not isinstance(self.edge_count, int) or self.edge_count < 0:
            raise ValidationError(message="Edge count must be a non-negative integer", param="edge_count")

        if not isinstance(self.is_public, bool):
            raise ValidationError(message="is_public must be a boolean value", param="is_public")

        if self.updated_at < self.created_at:
            raise ValidationError(message="Updated at cannot be before created at", param="updated_at")

    @classmethod
    def create(
        cls,
        name: str,
        tenant_id: str,
        domain: ScientificDomain,
        ontology_version_id: str,
        is_public: bool = False,
    ) -> "KnowledgeGraph":
        now = datetime.utcnow()
        kg_id = str(uuid.uuid4())

        return cls(
            id=kg_id,
            name=name,
            tenant_id=tenant_id,
            domain=domain,
            ontology_version_id=ontology_version_id,
            created_at=now,
            updated_at=now,
            node_count=0,
            edge_count=0,
            is_public=is_public,
        )

    def update_counts(self, node_count: int, edge_count: int) -> None:
        if not isinstance(node_count, int) or node_count < 0:
            raise ValidationError(message="Node count must be a non-negative integer", param="node_count")

        if not isinstance(edge_count, int) or edge_count < 0:
            raise ValidationError(message="Edge count must be a non-negative integer", param="edge_count")

        self.node_count = node_count
        self.edge_count = edge_count
        self.updated_at = datetime.utcnow()

    def set_public(self, is_public: bool) -> None:
        if not isinstance(is_public, bool):
            raise ValidationError(message="is_public must be a boolean value", param="is_public")

        self.is_public = is_public
        self.updated_at = datetime.utcnow()

