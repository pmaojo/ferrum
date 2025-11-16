"""Tests for domain entities using pydantic-v2 strict mode validation.

This test suite validates domain entities using pydantic-v2 strict mode to ensure
type safety and proper validation of all entity fields.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, ValidationError, ConfigDict

from domain.entities import (
    Triple, ValidationReport, GraphStreamEvent, GraphStreamEventType,
    Community, KnowledgeGraph, OntologyVersion, Document, Query,
    OntologyConstraint, ValidationError as DomainValidationError
)


# Pydantic models for strict validation of domain entities
class TripleModel(BaseModel):
    """Pydantic model for Triple validation."""
    model_config = ConfigDict(strict=True)

    subject: str
    predicate: str
    object: str
    tenant_id: str


class ValidationReportModel(BaseModel):
    """Pydantic model for ValidationReport validation."""
    model_config = ConfigDict(strict=True)

    is_consistent: bool
    unsat_classes: List[str]
    repair_suggestions: List[str]
    tenant_id: str
    ontology_version_id: str


class GraphStreamEventModel(BaseModel):
    """Pydantic model for GraphStreamEvent validation."""
    model_config = ConfigDict(strict=True)

    event_type: GraphStreamEventType
    data: Dict[str, Any]
    timestamp: datetime
    kg_id: str
    tenant_id: str


class CommunityModel(BaseModel):
    """Pydantic model for Community validation."""
    model_config = ConfigDict(strict=True)

    id: str
    centroid_embedding: List[float]
    node_ids: List[str]
    size: int
    tenant_id: str


class KnowledgeGraphModel(BaseModel):
    """Pydantic model for KnowledgeGraph validation."""
    model_config = ConfigDict(strict=True)

    id: str
    name: str
    tenant_id: str
    ontology_version_id: str
    created_at: datetime
    updated_at: datetime
    node_count: int
    edge_count: int


class OntologyVersionModel(BaseModel):
    """Pydantic model for OntologyVersion validation."""
    model_config = ConfigDict(strict=True)

    id: str
    checksum: str
    parent_version: Optional[str]
    tenant_id: str
    created_at: datetime
    axioms: List[str]


class DocumentModel(BaseModel):
    """Pydantic model for Document validation."""
    model_config = ConfigDict(strict=True)

    id: str
    content: str
    metadata: Dict[str, Any]
    processed_at: Optional[datetime]
    extraction_status: str
    tenant_id: str


class QueryModel(BaseModel):
    """Pydantic model for Query validation."""
    model_config = ConfigDict(strict=True)

    id: str
    natural_language: str
    translated_query: str
    execution_time_ms: float
    result_count: int
    user_id: str
    tenant_id: str
    kg_id: str


class OntologyConstraintModel(BaseModel):
    """Pydantic model for OntologyConstraint validation."""
    model_config = ConfigDict(strict=True)

    id: str
    constraint_type: str
    subject_class: str
    predicate: str
    object_constraint: str
    severity: str
    tenant_id: str


class ValidationErrorModel(BaseModel):
    """Pydantic model for ValidationError validation."""
    model_config = ConfigDict(strict=True)

    constraint_id: str
    triple: TripleModel
    error_message: str
    repair_suggestion: str
    tenant_id: str


class SharingLinkModel(BaseModel):
    """Pydantic model for SharingLink validation."""
    model_config = ConfigDict(strict=True)

    id: str
    kg_id: str
    tenant_id: str
    token: str
    permissions: List[str]
    expires_at: Optional[datetime]
    created_by: str


class TestDomainEntitiesValidation:
    """Test suite for domain entities validation using pydantic-v2 strict mode."""

    def test_triple_validation(self):
        """Test Triple entity validation."""
        # Valid Triple
        triple = Triple("subject", "predicate", "object", "tenant1")
        validated = TripleModel(
            subject=triple.subject,
            predicate=triple.predicate,
            object=triple.object,
            tenant_id=triple.tenant_id
        )

        assert validated.subject == triple.subject
        assert validated.predicate == triple.predicate
        assert validated.object == triple.object
        assert validated.tenant_id == triple.tenant_id

        # Invalid Triple - missing fields
        with pytest.raises(ValidationError):
            TripleModel(subject="subject", predicate="predicate")

    def test_validation_report_validation(self):
        """Test ValidationReport entity validation."""
        # Valid ValidationReport
        report = ValidationReport(
            is_consistent=True,
            unsat_classes=["Class1", "Class2"],
            repair_suggestions=["Fix class hierarchy"],
            tenant_id="tenant1",
            ontology_version_id="onto_v1"
        )

        validated = ValidationReportModel(
            is_consistent=report.is_consistent,
            unsat_classes=report.unsat_classes,
            repair_suggestions=report.repair_suggestions,
            tenant_id=report.tenant_id,
            ontology_version_id=report.ontology_version_id
        )

        assert validated.is_consistent == report.is_consistent
        assert validated.unsat_classes == report.unsat_classes
        assert validated.repair_suggestions == report.repair_suggestions
        assert validated.tenant_id == report.tenant_id
        assert validated.ontology_version_id == report.ontology_version_id

        # Invalid ValidationReport - wrong type
        with pytest.raises(ValidationError):
            ValidationReportModel(
                is_consistent="true",  # Should be boolean
                unsat_classes=["Class1"],
                repair_suggestions=["Fix"],
                tenant_id="tenant1",
                ontology_version_id="onto_v1"
            )

    def test_graph_stream_event_validation(self):
        """Test GraphStreamEvent entity validation."""
        # Valid GraphStreamEvent
        event = GraphStreamEvent(
            event_type=GraphStreamEventType.NODE_ADDED,
            data={"node_id": "node1", "label": "Person"},
            timestamp=datetime.now(timezone.utc),
            kg_id="kg1",
            tenant_id="tenant1"
        )

        validated = GraphStreamEventModel(
            event_type=event.event_type,
            data=event.data,
            timestamp=event.timestamp,
            kg_id=event.kg_id,
            tenant_id=event.tenant_id
        )

        assert validated.event_type == event.event_type
        assert validated.data == event.data
        assert validated.timestamp == event.timestamp
        assert validated.kg_id == event.kg_id
        assert validated.tenant_id == event.tenant_id

        # Invalid GraphStreamEvent - wrong event type
        with pytest.raises(ValidationError):
            GraphStreamEventModel(
                event_type="NODE_ADDED",  # Should be enum
                data={"node_id": "node1"},
                timestamp=datetime.now(),
                kg_id="kg1",
                tenant_id="tenant1"
            )

    def test_community_validation(self):
        """Test Community entity validation."""
        # Valid Community
        community = Community(
            id="community1",
            centroid_embedding=[0.1, 0.2, 0.3, 0.4],
            node_ids=["node1", "node2", "node3"],
            size=3,
            tenant_id="tenant1"
        )

        validated = CommunityModel(
            id=community.id,
            centroid_embedding=community.centroid_embedding,
            node_ids=community.node_ids,
            size=community.size,
            tenant_id=community.tenant_id
        )

        assert validated.id == community.id
        assert validated.centroid_embedding == community.centroid_embedding
        assert validated.node_ids == community.node_ids
        assert validated.size == community.size
        assert validated.tenant_id == community.tenant_id

        # Invalid Community - wrong embedding type
        with pytest.raises(ValidationError):
            CommunityModel(
                id="community1",
                centroid_embedding=["0.1", "0.2"],  # Should be floats
                node_ids=["node1", "node2"],
                size=2,
                tenant_id="tenant1"
            )

    def test_knowledge_graph_validation(self):
        """Test KnowledgeGraph entity validation."""
        # Valid KnowledgeGraph
        now = datetime.now(timezone.utc)
        kg = KnowledgeGraph(
            id="kg1",
            name="Test Graph",
            tenant_id="tenant1",
            ontology_version_id="onto_v1",
            created_at=now,
            updated_at=now,
            node_count=100,
            edge_count=150
        )

        validated = KnowledgeGraphModel(
            id=kg.id,
            name=kg.name,
            tenant_id=kg.tenant_id,
            ontology_version_id=kg.ontology_version_id,
            created_at=kg.created_at,
            updated_at=kg.updated_at,
            node_count=kg.node_count,
            edge_count=kg.edge_count
        )

        assert validated.id == kg.id
        assert validated.name == kg.name
        assert validated.tenant_id == kg.tenant_id
        assert validated.ontology_version_id == kg.ontology_version_id
        assert validated.created_at == kg.created_at
        assert validated.updated_at == kg.updated_at
        assert validated.node_count == kg.node_count
        assert validated.edge_count == kg.edge_count

        # Invalid KnowledgeGraph - negative counts
        with pytest.raises(ValidationError):
            KnowledgeGraphModel(
                id="kg1",
                name="Test Graph",
                tenant_id="tenant1",
                ontology_version_id="onto_v1",
                created_at=now,
                updated_at=now,
                node_count=-1,  # Should be positive
                edge_count=150
            )

    def test_ontology_version_validation(self):
        """Test OntologyVersion entity validation."""
        # Valid OntologyVersion
        now = datetime.now(timezone.utc)
        version = OntologyVersion(
            id="onto_v1",
            checksum="abc123",
            parent_version="onto_v0",
            tenant_id="tenant1",
            created_at=now,
            axioms=["Class: Person", "ObjectProperty: worksAt"]
        )

        validated = OntologyVersionModel(
            id=version.id,
            checksum=version.checksum,
            parent_version=version.parent_version,
            tenant_id=version.tenant_id,
            created_at=version.created_at,
            axioms=version.axioms
        )

        assert validated.id == version.id
        assert validated.checksum == version.checksum
        assert validated.parent_version == version.parent_version
        assert validated.tenant_id == version.tenant_id
        assert validated.created_at == version.created_at
        assert validated.axioms == version.axioms

        # Valid OntologyVersion with None parent
        version_no_parent = OntologyVersion(
            id="onto_v1",
            checksum="abc123",
            parent_version=None,
            tenant_id="tenant1",
            created_at=now,
            axioms=["Class: Person"]
        )

        validated_no_parent = OntologyVersionModel(
            id=version_no_parent.id,
            checksum=version_no_parent.checksum,
            parent_version=version_no_parent.parent_version,
            tenant_id=version_no_parent.tenant_id,
            created_at=version_no_parent.created_at,
            axioms=version_no_parent.axioms
        )

        assert validated_no_parent.parent_version is None

    def test_document_validation(self):
        """Test Document entity validation."""
        # Valid Document
        now = datetime.now(timezone.utc)
        doc = Document(
            id="doc1",
            content="Document content",
            metadata={"source": "web", "author": "John Doe"},
            processed_at=now,
            extraction_status="completed",
            tenant_id="tenant1"
        )

        validated = DocumentModel(
            id=doc.id,
            content=doc.content,
            metadata=doc.metadata,
            processed_at=doc.processed_at,
            extraction_status=doc.extraction_status,
            tenant_id=doc.tenant_id
        )

        assert validated.id == doc.id
        assert validated.content == doc.content
        assert validated.metadata == doc.metadata
        assert validated.processed_at == doc.processed_at
        assert validated.extraction_status == doc.extraction_status
        assert validated.tenant_id == doc.tenant_id

        # Valid Document with None processed_at
        doc_not_processed = Document(
            id="doc2",
            content="Document content",
            metadata={"source": "web"},
            processed_at=None,
            extraction_status="pending",
            tenant_id="tenant1"
        )

        validated_not_processed = DocumentModel(
            id=doc_not_processed.id,
            content=doc_not_processed.content,
            metadata=doc_not_processed.metadata,
            processed_at=doc_not_processed.processed_at,
            extraction_status=doc_not_processed.extraction_status,
            tenant_id=doc_not_processed.tenant_id
        )

        assert validated_not_processed.processed_at is None

    def test_query_validation(self):
        """Test Query entity validation."""
        # Valid Query
        query = Query(
            id="query1",
            natural_language="Who works at TechCorp?",
            translated_query="MATCH (p:Person)-[:worksAt]->(c:Company {name: 'TechCorp'}) RETURN p",
            execution_time_ms=42.5,
            result_count=3,
            user_id="user1",
            tenant_id="tenant1",
            kg_id="kg1"
        )

        validated = QueryModel(
            id=query.id,
            natural_language=query.natural_language,
            translated_query=query.translated_query,
            execution_time_ms=query.execution_time_ms,
            result_count=query.result_count,
            user_id=query.user_id,
            tenant_id=query.tenant_id,
            kg_id=query.kg_id
        )

        assert validated.id == query.id
        assert validated.natural_language == query.natural_language
        assert validated.translated_query == query.translated_query
        assert validated.execution_time_ms == query.execution_time_ms
        assert validated.result_count == query.result_count
        assert validated.user_id == query.user_id
        assert validated.tenant_id == query.tenant_id
        assert validated.kg_id == query.kg_id

        # Invalid Query - negative execution time
        with pytest.raises(ValidationError):
            QueryModel(
                id="query1",
                natural_language="Who works at TechCorp?",
                translated_query="MATCH (p:Person)-[:worksAt]->(c:Company) RETURN p",
                execution_time_ms=-10.5,  # Should be positive
                result_count=3,
                user_id="user1",
                tenant_id="tenant1",
                kg_id="kg1"
            )

    def test_ontology_constraint_validation(self):
        """Test OntologyConstraint entity validation."""
        # Valid OntologyConstraint
        constraint = OntologyConstraint(
            id="constraint1",
            constraint_type="domain",
            subject_class="Person",
            predicate="worksAt",
            object_constraint="Company",
            severity="error",
            tenant_id="tenant1"
        )

        validated = OntologyConstraintModel(
            id=constraint.id,
            constraint_type=constraint.constraint_type,
            subject_class=constraint.subject_class,
            predicate=constraint.predicate,
            object_constraint=constraint.object_constraint,
            severity=constraint.severity,
            tenant_id=constraint.tenant_id
        )

        assert validated.id == constraint.id
        assert validated.constraint_type == constraint.constraint_type
        assert validated.subject_class == constraint.subject_class
        assert validated.predicate == constraint.predicate
        assert validated.object_constraint == constraint.object_constraint
        assert validated.severity == constraint.severity
        assert validated.tenant_id == constraint.tenant_id

    def test_validation_error_validation(self):
        """Test ValidationError entity validation."""
        # Valid ValidationError
        triple = Triple("Person", "worksAt", "String", "tenant1")
        error = DomainValidationError(
            constraint_id="constraint1",
            triple=triple,
            error_message="Invalid range for worksAt",
            repair_suggestion="Use Company instead of String",
            tenant_id="tenant1"
        )

        validated = ValidationErrorModel(
            constraint_id=error.constraint_id,
            triple=TripleModel(
                subject=error.triple.subject,
                predicate=error.triple.predicate,
                object=error.triple.object,
                tenant_id=error.triple.tenant_id
            ),
            error_message=error.error_message,
            repair_suggestion=error.repair_suggestion,
            tenant_id=error.tenant_id
        )

        assert validated.constraint_id == error.constraint_id
        assert validated.triple.subject == error.triple.subject
        assert validated.triple.predicate == error.triple.predicate
        assert validated.triple.object == error.triple.object
        assert validated.error_message == error.error_message
        assert validated.repair_suggestion == error.repair_suggestion
        assert validated.tenant_id == error.tenant_id

    def test_sharing_link_validation(self):
        """Test SharingLink entity validation."""
        expires = datetime.now(timezone.utc) + timedelta(days=1)
        link = SharingLink(
            id="link1",
            kg_id="kg1",
            tenant_id="tenant1",
            token="tkn",
            permissions=["view"],
            expires_at=expires,
            created_by="user1",
        )

        validated = SharingLinkModel(
            id=link.id,
            kg_id=link.kg_id,
            tenant_id=link.tenant_id,
            token=link.token,
            permissions=link.permissions,
            expires_at=link.expires_at,
            created_by=link.created_by,
        )

        assert validated.id == link.id
        assert validated.kg_id == link.kg_id
        assert validated.token == link.token
        assert validated.permissions == link.permissions
        assert validated.tenant_id == link.tenant_id
        assert validated.created_by == link.created_by


if __name__ == "__main__":
    pytest.main(["-v", __file__])