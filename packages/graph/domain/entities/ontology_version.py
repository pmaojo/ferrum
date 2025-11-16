"""
Ontology Version Entity

Represents a versioned state of the ontology.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from .triple import Triple


class VersionStatus(Enum):
    """Status of an ontology version"""
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DRAFT = "DRAFT"
    DEPRECATED = "DEPRECATED"


@dataclass
class OntologyVersion:
    """Represents a versioned state of the ontology"""
    version_id: str
    tenant_id: str
    version_number: str
    status: VersionStatus
    created_at: datetime
    created_by: str
    description: Optional[str] = None
    parent_version_id: Optional[str] = None
    triples_count: int = 0
    components_count: int = 0
    relationships_count: int = 0
    checksum: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    # ------------------------------------------------------------------
    # Competency Question helpers
    # ------------------------------------------------------------------
    @property
    def competency_question_ids(self) -> List[str]:
        """Return competency question IDs stored in metadata.

        The IDs are stored under the ``competency_question_ids`` key in the
        ``metadata`` dictionary.  An empty list is returned when the key is not
        present.
        """

        return self.metadata.get("competency_question_ids", [])  # type: ignore[return-value]

    def set_competency_question_ids(self, cq_ids: List[str]) -> None:
        """Persist competency question identifiers into metadata."""

        self.metadata["competency_question_ids"] = cq_ids
    
    @property
    def is_active(self) -> bool:
        """Check if this version is active"""
        return self.status == VersionStatus.ACTIVE
    
    @property
    def is_draft(self) -> bool:
        """Check if this version is a draft"""
        return self.status == VersionStatus.DRAFT
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'version_id': self.version_id,
            'tenant_id': self.tenant_id,
            'version_number': self.version_number,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'description': self.description,
            'parent_version_id': self.parent_version_id,
            'triples_count': self.triples_count,
            'components_count': self.components_count,
            'relationships_count': self.relationships_count,
            'checksum': self.checksum,
            'metadata': self.metadata
        }


@dataclass
class VersionSnapshot:
    """Represents a complete snapshot of an ontology version"""
    version: OntologyVersion
    triples: List[Triple]
    architecture_json: Optional[Dict[str, Any]] = None
    validation_report: Optional[Dict[str, Any]] = None
    
    @property
    def total_triples(self) -> int:
        """Get total number of triples in this snapshot"""
        return len(self.triples)
    
    def get_triples_by_predicate(self, predicate: str) -> List[Triple]:
        """Get all triples with a specific predicate"""
        return [triple for triple in self.triples if triple.predicate == predicate]
    
    def get_triples_by_subject(self, subject: str) -> List[Triple]:
        """Get all triples with a specific subject"""
        return [triple for triple in self.triples if triple.subject == subject]
