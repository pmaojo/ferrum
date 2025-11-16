"""Unit tests for CreateKnowledgeGraphUseCase."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from domain.entities import KnowledgeGraph, ScientificDomain, OntologyVersion
from application.exceptions import ValidationError, BusinessRuleViolationError
from application.use_cases.knowledge_graph.create_knowledge_graph_use_case import (
    CreateKnowledgeGraphUseCase,
    CreateKnowledgeGraphRequest,
    CreateKnowledgeGraphResponse,
    KnowledgeGraphDTO
)
from application.ports.contract import ContractPort


class TestCreateKnowledgeGraphUseCase:
    """Test cases for CreateKnowledgeGraphUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.kg_repository = Mock()
        self.ontology_repository = Mock()
        self.ontology_validator = Mock()
        self.subscription_service = Mock()
        self.metadata_repository = Mock()
        self.tracer = Mock()
        self.contract_adapter = Mock(spec=ContractPort)

        # Mock tracer span
        self.mock_span = Mock()
        self.tracer.start_span.return_value.__enter__ = Mock(return_value=self.mock_span)
        self.tracer.start_span.return_value.__exit__ = Mock(return_value=None)

        self.use_case = CreateKnowledgeGraphUseCase(
            kg_repository=self.kg_repository,
            ontology_repository=self.ontology_repository,
            ontology_validator=self.ontology_validator,
            subscription_service=self.subscription_service,
            metadata_repository=self.metadata_repository,
            tracer=self.tracer,
            contract_adapter=self.contract_adapter,
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_creation(self):
        """Test successful knowledge graph creation."""
        # Arrange
        request = CreateKnowledgeGraphRequest(
            name="Test KG",
            description="Test description",
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="onto-123",
            tenant_id="tenant-123",
            user_id="user-123",
            is_public=False
        )

        # Mock repository responses
        self.kg_repository.get_by_name.return_value = None  # No existing KG
        self.ontology_repository.get_by_id.return_value = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=["A"]
        )

        created_kg = KnowledgeGraph.create(
            name="Test KG",
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="onto-123",
            is_public=False
        )
        self.kg_repository.create.return_value = created_kg

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.knowledge_graph is not None
        assert response.knowledge_graph.name == "Test KG"
        assert response.knowledge_graph.domain == "biology"
        assert response.knowledge_graph.tenant_id == "tenant-123"
        assert response.knowledge_graph.ontology_version_id == "onto-123"
        assert response.knowledge_graph.is_public is False

        # Verify repository calls
        self.kg_repository.get_by_name.assert_called_once_with("Test KG", "tenant-123")
        self.ontology_repository.get_by_id.assert_called_once_with("onto-123", "tenant-123")
        self.kg_repository.create.assert_called_once()

        # Verify subscription check
        self.subscription_service.check_knowledge_graph_limit.assert_called_once_with("tenant-123")

        # Verify description persisted
        self.metadata_repository.save_description.assert_called_once_with(
            kg_id=created_kg.id,
            tenant_id="tenant-123",
            description="Test description",
        )

        # Verify metrics
        self.tracer.record_metric.assert_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_empty_name(self):
        """Test validation error when name is empty."""
        # Arrange
        request = CreateKnowledgeGraphRequest(
            name="",
            description=None,
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="onto-123",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "name is required" in str(exc_info.value)
        assert exc_info.value.field == "name"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_long_name(self):
        """Test validation error when name is too long."""
        # Arrange
        request = CreateKnowledgeGraphRequest(
            name="x" * 256,  # Too long
            description=None,
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="onto-123",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "cannot exceed 255 characters" in str(exc_info.value)
        assert exc_info.value.field == "name"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_empty_tenant_id(self):
        """Test validation error when tenant_id is empty."""
        # Arrange
        request = CreateKnowledgeGraphRequest(
            name="Test KG",
            description=None,
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="onto-123",
            tenant_id="",
            user_id="user-123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "Tenant ID is required" in str(exc_info.value)
        assert exc_info.value.field == "tenant_id"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_empty_ontology_version_id(self):
        """Test validation error when ontology_version_id is empty."""
        # Arrange
        request = CreateKnowledgeGraphRequest(
            name="Test KG",
            description=None,
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "Ontology version ID is required" in str(exc_info.value)
        assert exc_info.value.field == "ontology_version_id"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_long_description(self):
        """Test validation error when description is too long."""
        # Arrange
        request = CreateKnowledgeGraphRequest(
            name="Test KG",
            description="x" * 1001,  # Too long
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="onto-123",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "Description cannot exceed 1000 characters" in str(exc_info.value)
        assert exc_info.value.field == "description"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_business_rule_violation_duplicate_name(self):
        """Test business rule violation when KG with same name exists."""
        # Arrange
        request = CreateKnowledgeGraphRequest(
            name="Test KG",
            description=None,
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="onto-123",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        self.ontology_repository.get_by_id.return_value = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=["A"]
        )

        # Mock existing KG with same name
        existing_kg = KnowledgeGraph.create(
            name="Test KG",
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="onto-123"
        )
        self.kg_repository.get_by_name.return_value = existing_kg

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False
        assert "already exists" in response.error_message

        # Verify repository was checked but not called for creation
        self.kg_repository.get_by_name.assert_called_once_with("Test KG", "tenant-123")
        self.ontology_repository.get_by_id.assert_called_once_with("onto-123", "tenant-123")
        self.kg_repository.create.assert_not_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_subscription_limit_exceeded(self):
        """Test subscription limit exceeded."""
        # Arrange
        request = CreateKnowledgeGraphRequest(
            name="Test KG",
            description=None,
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="onto-123",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        self.ontology_repository.get_by_id.return_value = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=["A"]
        )

        # Mock subscription service to raise limit error
        self.subscription_service.check_knowledge_graph_limit.side_effect = BusinessRuleViolationError(
            message="Knowledge graph limit exceeded",
            rule_name="kg_limit"
        )

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False
        assert "limit exceeded" in response.error_message

        # Verify subscription check was called
        self.subscription_service.check_knowledge_graph_limit.assert_called_once_with("tenant-123")

        # Verify repository was not called
        self.ontology_repository.get_by_id.assert_not_called()
        self.kg_repository.create.assert_not_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_with_public_knowledge_graph(self):
        """Test creating a public knowledge graph."""
        # Arrange
        request = CreateKnowledgeGraphRequest(
            name="Public KG",
            description=None,
            domain=ScientificDomain.GENERAL,
            ontology_version_id="onto-123",
            tenant_id="tenant-123",
            user_id="user-123",
            is_public=True
        )

        # Mock repository responses
        self.kg_repository.get_by_name.return_value = None
        self.ontology_repository.get_by_id.return_value = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.GENERAL,
            axioms=["A"]
        )

        created_kg = KnowledgeGraph.create(
            name="Public KG",
            tenant_id="tenant-123",
            domain=ScientificDomain.GENERAL,
            ontology_version_id="onto-123",
            is_public=True
        )
        self.kg_repository.create.return_value = created_kg

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.knowledge_graph.is_public is True
        assert response.knowledge_graph.domain == "general"
        self.ontology_repository.get_by_id.assert_called_once_with("onto-123", "tenant-123")

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_different_scientific_domains(self):
        """Test creating knowledge graphs with different scientific domains."""
        domains = [
            ScientificDomain.BIOLOGY,
            ScientificDomain.CHEMISTRY,
            ScientificDomain.PHYSICS,
            ScientificDomain.MEDICINE,
            ScientificDomain.ENVIRONMENTAL_SCIENCE,
            ScientificDomain.ASTRONOMY
        ]

        for domain in domains:
            # Arrange
            request = CreateKnowledgeGraphRequest(
                name=f"Test KG {domain.value}",
                description=None,
                domain=domain,
                ontology_version_id="onto-123",
                tenant_id="tenant-123",
                user_id="user-123"
            )

            # Mock repository responses
            self.kg_repository.get_by_name.return_value = None

            self.ontology_repository.get_by_id.return_value = OntologyVersion.create(
                tenant_id="tenant-123",
                domain=domain,
                axioms=["A"]
            )

            created_kg = KnowledgeGraph.create(
                name=f"Test KG {domain.value}",
                tenant_id="tenant-123",
                domain=domain,
                ontology_version_id="onto-123"
            )
            self.kg_repository.create.return_value = created_kg

            # Act
            response = await self.use_case.execute(request)

            # Assert
            assert response.success is True
            assert response.knowledge_graph.domain == domain.value

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_contract_verification_per_batch(self):
        """Verify contract is checked after each triplet batch."""

        request = CreateKnowledgeGraphRequest(
            name="Contract KG",
            description=None,
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="onto-123",
            tenant_id="tenant-123",
            user_id="user-123",
            triplet_batches=[[('a', 'p', 'b')], [('b', 'p', 'c')]],
        )

        self.kg_repository.get_by_name.return_value = None
        self.ontology_repository.get_by_id.return_value = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=["A"],
        )

        created_kg = KnowledgeGraph.create(
            name="Contract KG",
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="onto-123",
        )
        self.kg_repository.create.return_value = created_kg

        # First batch violates contract, second passes
        self.contract_adapter.verify.side_effect = [(False, []), (True, [])]

        await self.use_case.execute(request)

        assert self.contract_adapter.verify.call_count == 2
        self.contract_adapter.repair.assert_called_once()
