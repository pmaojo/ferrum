"""Unit tests for IngestionService using mock ports."""

import logging
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from typing import List

from domain.entities import (
    Triple, ValidationReport, Document, GraphStreamEventType, ScientificDomain
)
from domain.services import IngestionService, GraphRAGException
from application.ports import GraphRetrieverPort, OntologyValidatorPort, TracingPort


class TestIngestionService:
    """Test suite for IngestionService domain service."""

    @pytest.fixture
    def mock_retriever(self) -> Mock:
        """Mock GraphRetrieverPort for testing."""
        mock = Mock(spec=GraphRetrieverPort)
        return mock

    @pytest.fixture
    def mock_validator(self) -> Mock:
        """Mock OntologyValidatorPort for testing."""
        mock = Mock(spec=OntologyValidatorPort)
        return mock

    @pytest.fixture
    def mock_tracer(self) -> Mock:
        """Mock TracingPort for testing."""
        mock = Mock(spec=TracingPort)
        mock.start_span.return_value = MagicMock()
        return mock

    @pytest.fixture
    def sample_documents(self) -> List[Document]:
        """Sample documents for testing."""
        return [
            Document(
                id="doc1",
                content="Alice works at TechCorp as a software engineer.",
                metadata={"source": "hr_system"},
                processed_at=None,
                extraction_status="pending",
                tenant_id="tenant1"
            ),
            Document(
                id="doc2",
                content="Bob manages the engineering team at TechCorp.",
                metadata={"source": "org_chart"},
                processed_at=None,
                extraction_status="pending",
                tenant_id="tenant1"
            )
        ]

    @pytest.fixture
    def sample_triples(self) -> List[Triple]:
        """Sample triples for testing."""
        return [
            Triple("Alice", "worksAt", "TechCorp", "tenant1"),
            Triple("Alice", "hasRole", "SoftwareEngineer", "tenant1"),
            Triple("Bob", "manages", "EngineeringTeam", "tenant1"),
            Triple("Bob", "worksAt", "TechCorp", "tenant1")
        ]

    @pytest.fixture
    def ingestion_service(
        self,
        mock_retriever: Mock,
        mock_validator: Mock,
        mock_tracer: Mock
    ) -> IngestionService:
        """IngestionService instance with mocked dependencies."""
        test_logger = logging.getLogger("test.ingestion_service")
        return IngestionService(
            retriever=mock_retriever,
            validator=mock_validator,
            tracer=mock_tracer,
            logger=test_logger,
        )

    def test_successful_document_processing(
        self,
        ingestion_service: IngestionService,
        mock_retriever: Mock,
        mock_validator: Mock,
        mock_tracer: Mock,
        sample_documents: List[Document],
        sample_triples: List[Triple]
    ):
        """Test successful document processing with valid triples.

        Requirements tested:
        - 1.1: Document processing through GraphRAG extraction
        - 1.2: Ontological validation of extracted knowledge
        """
        # Arrange
        kg_id = "kg123"
        tenant_id = "tenant1"
        ontology_version_id = "onto_v1"

        mock_retriever.index.return_value = sample_triples
        mock_validator.validate_delta.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id
        )

        # Act
        result = ingestion_service.process_documents(
            documents=sample_documents,
            kg_id=kg_id,
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id
        )

        # Assert
        assert result.is_consistent is True
        assert len(result.unsat_classes) == 0
        assert result.tenant_id == tenant_id
        assert result.ontology_version_id == ontology_version_id

        # Verify port interactions
        mock_retriever.index.assert_called_once_with(
            docs=[doc.content for doc in sample_documents],
            kg_id=kg_id,
            tenant_id=tenant_id
        )
        mock_validator.validate_delta.assert_called_once_with(
            new_triples=sample_triples,
            existing_version_id=ontology_version_id,
            tenant_id=tenant_id
        )

        # Verify tracing calls
        mock_tracer.start_span.assert_called_once()
        assert mock_tracer.record_metric.call_count == 2  # triples_extracted and validation_success

    def test_validation_failure_with_repair_suggestions(
        self,
        ingestion_service: IngestionService,
        mock_retriever: Mock,
        mock_validator: Mock,
        sample_documents: List[Document],
        sample_triples: List[Triple]
    ):
        """Test handling of validation failures with repair suggestions.

        Requirements tested:
        - 1.3: Error handling with repair suggestions
        - 8.3: Validation failure handling
        """
        # Arrange
        kg_id = "kg123"
        tenant_id = "tenant1"
        ontology_version_id = "onto_v1"

        mock_retriever.index.return_value = sample_triples
        mock_validator.validate_delta.return_value = ValidationReport(
            is_consistent=False,
            unsat_classes=["SoftwareEngineer", "EngineeringTeam"],
            repair_suggestions=["Check class hierarchy", "Verify domain constraints"],
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id
        )

        # Act
        result = ingestion_service.process_documents(
            documents=sample_documents,
            kg_id=kg_id,
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id
        )

        # Assert
        assert result.is_consistent is False
        assert len(result.unsat_classes) == 2
        assert "SoftwareEngineer" in result.unsat_classes
        assert "EngineeringTeam" in result.unsat_classes
        assert len(result.repair_suggestions) > 2  # Original + enhanced suggestions
        assert any("Review class definitions" in suggestion for suggestion in result.repair_suggestions)

    def test_no_triples_extracted(
        self,
        ingestion_service: IngestionService,
        mock_retriever: Mock,
        mock_validator: Mock,
        sample_documents: List[Document]
    ):
        """Test handling when no triples are extracted from documents."""
        # Arrange
        kg_id = "kg123"
        tenant_id = "tenant1"
        ontology_version_id = "onto_v1"

        mock_retriever.index.return_value = []  # No triples extracted

        # Act
        result = ingestion_service.process_documents(
            documents=sample_documents,
            kg_id=kg_id,
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id
        )

        # Assert
        assert result.is_consistent is True  # No triples to validate
        assert len(result.repair_suggestions) == 1
        assert "No knowledge extracted" in result.repair_suggestions[0]

        # Validator should not be called
        mock_validator.validate_delta.assert_not_called()
        mock_validator.validate.assert_not_called()

    def test_graphrag_extraction_failure_with_retry(
        self,
        ingestion_service: IngestionService,
        mock_retriever: Mock,
        mock_validator: Mock,
        mock_tracer: Mock,
        sample_documents: List[Document]
    ):
        """Test GraphRAG extraction failure handling with retry logic."""
        # Arrange
        kg_id = "kg123"
        tenant_id = "tenant1"
        ontology_version_id = "onto_v1"

        # Mock retriever to fail on first two attempts, succeed on third
        mock_retriever.index.side_effect = [
            Exception("Network timeout"),
            Exception("Service unavailable"),
            [Triple("Alice", "worksAt", "TechCorp", tenant_id)]  # Success on third attempt
        ]

        mock_validator.validate_delta.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id
        )

        # Act
        result = ingestion_service.process_documents(
            documents=sample_documents,
            kg_id=kg_id,
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id
        )

        # Assert
        assert result.is_consistent is True
        assert mock_retriever.index.call_count == 3  # Two failures + one success

        # Verify error metric was not recorded (since it eventually succeeded)
        error_metrics = [call for call in mock_tracer.record_metric.call_args_list
                        if call[1]['name'] == 'ingestion.processing_errors']
        assert len(error_metrics) == 0

    def test_graphrag_extraction_complete_failure(
        self,
        ingestion_service: IngestionService,
        mock_retriever: Mock,
        mock_tracer: Mock,
        sample_documents: List[Document]
    ):
        """Test complete GraphRAG extraction failure after all retries."""
        # Arrange
        kg_id = "kg123"
        tenant_id = "tenant1"
        ontology_version_id = "onto_v1"

        mock_retriever.index.side_effect = Exception("Persistent failure")

        # Act & Assert
        with pytest.raises(GraphRAGException) as exc_info:
            ingestion_service.process_documents(
                documents=sample_documents,
                kg_id=kg_id,
                tenant_id=tenant_id,
                ontology_version_id=ontology_version_id
            )

        assert exc_info.value.error_code == "INGESTION_FAILED"
        assert "Document processing failed" in exc_info.value.message
        assert exc_info.value.context["kg_id"] == kg_id
        assert exc_info.value.context["tenant_id"] == tenant_id

        # Verify error metric was recorded
        mock_tracer.record_metric.assert_called()
        error_calls = [call for call in mock_tracer.record_metric.call_args_list
                      if call[1]['name'] == 'ingestion.processing_errors']
        assert len(error_calls) == 1

    def test_full_validation_mode(
        self,
        ingestion_service: IngestionService,
        mock_retriever: Mock,
        mock_validator: Mock,
        sample_documents: List[Document],
        sample_triples: List[Triple]
    ):
        """Test full validation mode instead of incremental."""
        # Arrange
        kg_id = "kg123"
        tenant_id = "tenant1"
        ontology_version_id = "onto_v1"

        mock_retriever.index.return_value = sample_triples
        mock_validator.validate.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id
        )

        # Act
        result = ingestion_service.process_documents(
            documents=sample_documents,
            kg_id=kg_id,
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id,
            validate_incrementally=False  # Use full validation
        )

        # Assert
        assert result.is_consistent is True

        # Verify full validation was used instead of delta
        mock_validator.validate.assert_called_once_with(
            triples=sample_triples,
            ontology_version_id=ontology_version_id
        )
        mock_validator.validate_delta.assert_not_called()

    def test_validation_process_failure_handling(
        self,
        ingestion_service: IngestionService,
        mock_retriever: Mock,
        mock_validator: Mock,
        sample_documents: List[Document],
        sample_triples: List[Triple]
    ):
        """Test handling when validation process itself fails."""
        # Arrange
        kg_id = "kg123"
        tenant_id = "tenant1"
        ontology_version_id = "onto_v1"

        mock_retriever.index.return_value = sample_triples
        mock_validator.validate_delta.side_effect = Exception("Ontology service unavailable")

        # Act
        result = ingestion_service.process_documents(
            documents=sample_documents,
            kg_id=kg_id,
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id
        )

        # Assert - Should return validation failure report instead of raising exception
        assert result.is_consistent is False
        assert "ValidationProcessFailed" in result.unsat_classes
        assert any("Validation process failed" in suggestion for suggestion in result.repair_suggestions)
        assert any("Check ontology version availability" in suggestion for suggestion in result.repair_suggestions)

    def test_service_without_tracer(
        self,
        mock_retriever: Mock,
        mock_validator: Mock,
        sample_documents: List[Document],
        sample_triples: List[Triple]
    ):
        """Test service operation without tracing capabilities."""
        # Arrange
        service = IngestionService(
            retriever=mock_retriever,
            validator=mock_validator,
            tracer=None,  # No tracer
            logger=logging.getLogger("test.ingestion_service"),
        )

        kg_id = "kg123"
        tenant_id = "tenant1"
        ontology_version_id = "onto_v1"

        mock_retriever.index.return_value = sample_triples
        mock_validator.validate_delta.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id
        )

        # Act
        result = service.process_documents(
            documents=sample_documents,
            kg_id=kg_id,
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id
        )

        # Assert
        assert result.is_consistent is True
        # Should work fine without tracer

    def test_repair_suggestion_enhancement(
        self,
        ingestion_service: IngestionService,
        mock_retriever: Mock,
        mock_validator: Mock,
        sample_documents: List[Document]
    ):
        """Test enhancement of repair suggestions with context-specific guidance."""
        # Arrange
        kg_id = "kg123"
        tenant_id = "tenant1"
        ontology_version_id = "onto_v1"

        # Create triples with many unique predicates to trigger specific suggestions
        many_predicate_triples = [
            Triple("Entity1", f"predicate{i}", f"Value{i}", tenant_id)
            for i in range(60)  # More than 50 unique predicates
        ]

        mock_retriever.index.return_value = many_predicate_triples
        mock_validator.validate_delta.return_value = ValidationReport(
            is_consistent=False,
            unsat_classes=["TestClass1", "TestClass2"],
            repair_suggestions=["Original suggestion"],
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id
        )

        # Act
        result = ingestion_service.process_documents(
            documents=sample_documents,
            kg_id=kg_id,
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id
        )

        # Assert
        assert result.is_consistent is False
        suggestions = result.repair_suggestions

        # Should contain original suggestion
        assert "Original suggestion" in suggestions

        # Should contain class-specific suggestions
        assert any("Review class definitions for: TestClass1, TestClass2" in s for s in suggestions)

        # Should contain predicate-specific suggestion due to many predicates
        assert any("Large number of unique predicates detected" in s for s in suggestions)

        # Should contain general guidance
        assert any("Use ontology visualization tools" in s for s in suggestions)
        assert any("Consider incremental validation" in s for s in suggestions)

    def test_scientific_domain_processing(
        self,
        ingestion_service: IngestionService,
        mock_retriever: Mock,
        mock_validator: Mock,
        mock_tracer: Mock,
        sample_documents: List[Document],
        sample_triples: List[Triple]
    ):
        """Test document processing with scientific domain specification.

        Requirements tested:
        - 11.1: Scientific domain support for specialized processing
        """
        # Arrange
        kg_id = "kg123"
        tenant_id = "tenant1"
        ontology_version_id = "onto_v1"
        domain = ScientificDomain.BIOLOGY

        mock_retriever.index.return_value = sample_triples
        mock_validator.validate_delta.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id
        )

        # Act
        result = ingestion_service.process_documents(
            documents=sample_documents,
            kg_id=kg_id,
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id,
            domain=domain
        )

        # Assert
        assert result.is_consistent is True
        assert result.tenant_id == tenant_id
        assert result.ontology_version_id == ontology_version_id

        # Verify port interactions
        mock_retriever.index.assert_called_once_with(
            docs=[doc.content for doc in sample_documents],
            kg_id=kg_id,
            tenant_id=tenant_id
        )

        # Verify tracing includes domain context
        mock_tracer.start_span.assert_called_once()
        span_call_kwargs = mock_tracer.start_span.call_args[1]
        assert span_call_kwargs["tenant_id"] == tenant_id
        assert span_call_kwargs["kg_id"] == kg_id

    def test_preserves_explanation_from_validator(
        self,
        ingestion_service: IngestionService,
        mock_retriever: Mock,
        mock_validator: Mock,
        sample_documents: List[Document],
        sample_triples: List[Triple],
    ):
        """Ensure explanation from validator is returned."""
        kg_id = "kg123"
        tenant_id = "tenant1"
        ontology_version_id = "onto_v1"

        mock_retriever.index.return_value = sample_triples
        mock_validator.validate_delta.return_value = ValidationReport(
            is_consistent=False,
            unsat_classes=["Foo"],
            repair_suggestions=["Fix"],
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id,
            explanation="because",
        )

        result = ingestion_service.process_documents(
            documents=sample_documents,
            kg_id=kg_id,
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id,
        )

        assert result.explanation == "because"


if __name__ == "__main__":
    pytest.main([__file__])