"""Core domain entities with multi-tenancy support."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..exceptions import ValidationError
from .enums import DataRetentionTarget
from .knowledge_graph import Triple


@dataclass
class Document:
    """Document entity for knowledge extraction."""

    id: str
    content: str
    metadata: Dict[str, Any]
    processed_at: Optional[datetime]
    extraction_status: str
    tenant_id: str


@dataclass
class Query:
    """Query entity with execution context."""

    id: str
    natural_language: str
    translated_query: str
    execution_time_ms: float
    result_count: int
    user_id: str
    tenant_id: str
    kg_id: str


@dataclass
class DataRetentionPolicy:
    """Policy defining data retention rules for a tenant."""

    tenant_id: str
    retention_days: int
    applies_to: DataRetentionTarget

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValidationError(message="Tenant ID must be a non-empty string", param="tenant_id")

        if not isinstance(self.retention_days, int) or self.retention_days <= 0:
            raise ValidationError(message="retention_days must be a positive integer", param="retention_days")

        if not isinstance(self.applies_to, DataRetentionTarget):
            raise ValidationError(message="applies_to must be a DataRetentionTarget", param="applies_to")


@dataclass
class OntologyConstraint:
    """Ontology constraint for validation."""

    id: str
    constraint_type: str  # domain, range, cardinality, disjoint
    subject_class: str
    predicate: str
    object_constraint: str
    severity: str  # error, warning
    tenant_id: str


@dataclass
class ValidationError:
    """Validation error with repair suggestions."""

    constraint_id: str
    triple: Triple
    error_message: str
    repair_suggestion: str
    tenant_id: str

