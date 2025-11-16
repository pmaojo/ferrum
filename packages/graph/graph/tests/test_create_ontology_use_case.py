"""Tests for CreateOntologyUseCase."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from typing import List, Optional

from domain.entities import OntologyVersion, ScientificDomain, ValidationReport
from application.exceptions import (
    ValidationError,
    BusinessRuleViolationError,
    NotFoundError,
    ApplicationError
)
from application.use_cases.ontology.create_ontology_use_case import (
    CreateOntologyUseCase,
    CreateOntologyResponse,
    OntologyRepositoryPort,
    SubscriptionServicePort,
    OntologyParserPort,
)
from application.use_cases.dto import CreateOntologyRequestDTO, OntologyDTO
from application.ports import OntologyValidatorPort, TracingPort, OwlAxiomGeneratorPort
from application.ports.contract import ContractPort
from application.contracts import Contract


class TestCreateOntologyUseCase:
    """Test cases for CreateOntologyUseCase."""

    @pytest.fixture
    def mock_ontology_repository(self):
        """Mock ontology repository."""
        repo = Mock(spec=OntologyRepositoryPort)
        repo.get_version_name.return_value = None
        return repo

    @pytest.fixture
    def mock_ontology_validator(self):
        """Mock ontology validator."""
        return Mock(spec=OntologyValidatorPort)

    @pytest.fixture
    def mock_ontology_parser(self):
        """Mock ontology parser."""
        return Mock(spec=OntologyParserPort)

    @pytest.fixture
    def mock_subscription_service(self):
        """Mock subscription service."""
        return Mock(spec=SubscriptionServicePort)

    @pytest.fixture
    def mock_axiom_generator(self):
        """Mock axiom generator."""
        return Mock(spec=OwlAxiomGeneratorPort)

    @pytest.fixture
    def mock_contract_adapter(self):
        """Mock contract adapter."""
        return Mock(spec=ContractPort)

    @pytest.fixture
    def mock_tracer(self):
        """Mock tracer."""
        tracer = Mock(spec=TracingPort)
        tracer.start_span.return_value.__enter__ = Mock()
        tracer.start_span.return_value.__exit__ = Mock()
        return tracer

    @pytest.fixture
    def use_case(
        self,
        mock_ontology_repository,
        mock_ontology_validator,
        mock_ontology_parser,
        mock_subscription_service,
        mock_tracer,
        mock_axiom_generator,
        mock_contract_adapter,
    ):
        """Create use case instance with mocked dependencies."""
        return CreateOntologyUseCase(
            ontology_repository=mock_ontology_repository,
            ontology_validator=mock_ontology_validator,
            ontology_parser=mock_ontology_parser,
            subscription_service=mock_subscription_service,
            tracer=mock_tracer,
            axiom_generator=mock_axiom_generator,
            contract_adapter=mock_contract_adapter,
        )

    @pytest.fixture
    def valid_request(self):
        """Valid create ontology request."""
        return CreateOntologyRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Test Ontology",
            description="A test ontology",
            domain="biology",
            content="<owl:Ontology>...</owl:Ontology>",
            format="owl"
        )

    @pytest.fixture
    def sample_axioms(self):
        """Sample axioms for testing."""
        return [
            "Class: Person",
            "Class: Animal",
            "ObjectProperty: hasParent"
        ]

    @pytest.fixture
    def sample_ontology_version(self, sample_axioms):
        """Sample ontology version for testing."""
        return OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=sample_axioms
        )

    @pytest.mark.asyncio
    async def test_create_ontology_success(self, use_case, valid_request, sample_axioms,
                                         sample_ontology_version, mock_ontology_repository,
                                         mock_ontology_validator, mock_ontology_parser,
                                         mock_subscription_service):
        """Test successful ontology creation."""
        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_ontology_parser.parse_content.return_value = sample_axioms
        mock_ontology_validator.validate.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id="tenant-123",
            ontology_version_id=sample_ontology_version.id
        )
        mock_ontology_repository.create.return_value = sample_ontology_version

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is True
        assert response.ontology is not None
        assert response.ontology.name == "Test Ontology"
        assert response.ontology.domain == "biology"
        assert response.ontology.axiom_count == 3
        assert response.error_message is None

        # Verify mock calls
        mock_subscription_service.check_ontology_limit.assert_called_once_with("tenant-123")
        mock_ontology_repository.get_by_name_and_domain.assert_called_once_with(
            "Test Ontology", ScientificDomain.BIOLOGY, "tenant-123"
        )
        mock_ontology_parser.parse_content.assert_called_once_with(
            "<owl:Ontology>...</owl:Ontology>", "owl"
        )
        mock_ontology_validator.validate.assert_called_once()
        mock_ontology_repository.create.assert_called_once()
        mock_ontology_repository.set_version_name.assert_called_once_with(
            sample_ontology_version.id,
            "Test Ontology",
            "tenant-123",
        )

    @pytest.mark.asyncio
    async def test_create_ontology_with_parent_success(self, use_case, valid_request,
                                                     sample_axioms, sample_ontology_version,
                                                     mock_ontology_repository, mock_ontology_validator,
                                                     mock_ontology_parser, mock_subscription_service):
        """Test successful ontology creation with parent version."""
        # Setup request with parent
        valid_request.parent_version_id = "parent-123"

        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_ontology_repository.get_by_id.return_value = sample_ontology_version
        mock_ontology_parser.parse_content.return_value = sample_axioms
        mock_ontology_validator.validate.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id="tenant-123",
            ontology_version_id=sample_ontology_version.id
        )

        child_version = OntologyVersion.create_child_version(
            parent=sample_ontology_version,
            axioms=sample_axioms
        )
        mock_ontology_repository.create.return_value = child_version

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is True
        assert response.ontology is not None
        assert response.ontology.parent_version_id == sample_ontology_version.id

        # Verify parent validation was called
        mock_ontology_repository.get_by_id.assert_called_once_with("parent-123", "tenant-123")
        mock_ontology_repository.set_version_name.assert_called_once_with(
            child_version.id,
            "Test Ontology",
            "tenant-123",
        )

    @pytest.mark.asyncio
    async def test_create_ontology_validation_errors(self, use_case):
        """Test validation errors for invalid requests."""
        test_cases = [
            # Empty name
            {
                "request": CreateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    name="",
                    domain="biology",
                    content="content",
                    format="owl"
                ),
                "expected_field": "name"
            },
            # Missing tenant_id
            {
                "request": CreateOntologyRequestDTO(
                    tenant_id="",
                    user_id="user-456",
                    name="Test",
                    domain="biology",
                    content="content",
                    format="owl"
                ),
                "expected_field": "tenant_id"
            },
            # Missing user_id
            {
                "request": CreateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="",
                    name="Test",
                    domain="biology",
                    content="content",
                    format="owl"
                ),
                "expected_field": "user_id"
            },
            # Empty content
            {
                "request": CreateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    name="Test",
                    domain="biology",
                    content="",
                    format="owl"
                ),
                "expected_field": "content"
            },
            # Invalid domain
            {
                "request": CreateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    name="Test",
                    domain="invalid_domain",
                    content="content",
                    format="owl"
                ),
                "expected_field": "domain"
            },
            # Invalid format
            {
                "request": CreateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    name="Test",
                    domain="biology",
                    content="content",
                    format="invalid_format"
                ),
                "expected_field": "format"
            },
            # Name too long
            {
                "request": CreateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    name="x" * 256,
                    domain="biology",
                    content="content",
                    format="owl"
                ),
                "expected_field": "name"
            },
            # Description too long
            {
                "request": CreateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    name="Test",
                    description="x" * 1001,
                    domain="biology",
                    content="content",
                    format="owl"
                ),
                "expected_field": "description"
            }
        ]

        for test_case in test_cases:
            with pytest.raises(ValidationError) as exc_info:
                await use_case.execute(test_case["request"])

            assert exc_info.value.field == test_case["expected_field"]

    @pytest.mark.asyncio
    async def test_create_ontology_subscription_limit_exceeded(self, use_case, valid_request,
                                                             mock_subscription_service):
        """Test subscription limit exceeded error."""
        # Setup mock to raise limit exceeded error
        mock_subscription_service.check_ontology_limit.side_effect = BusinessRuleViolationError(
            message="Ontology limit exceeded",
            rule_name="ontology_limit"
        )

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is False
        assert "Ontology limit exceeded" in response.error_message

    @pytest.mark.asyncio
    async def test_create_ontology_duplicate_name_domain(self, use_case, valid_request,
                                                       sample_ontology_version,
                                                       mock_ontology_repository,
                                                       mock_subscription_service):
        """Test duplicate ontology name and domain error."""
        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = sample_ontology_version

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is False
        assert "already exists" in response.error_message

    @pytest.mark.asyncio
    async def test_create_ontology_parent_not_found(self, use_case, valid_request,
                                                   mock_ontology_repository,
                                                   mock_subscription_service):
        """Test parent version not found error."""
        # Setup request with parent
        valid_request.parent_version_id = "nonexistent-parent"

        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_ontology_repository.get_by_id.return_value = None

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is False
        assert "not found" in response.error_message

    @pytest.mark.asyncio
    async def test_create_ontology_parent_domain_mismatch(self, use_case, valid_request,
                                                        sample_ontology_version,
                                                        mock_ontology_repository,
                                                        mock_subscription_service):
        """Test parent domain mismatch error."""
        # Setup request with parent and different domain
        valid_request.parent_version_id = "parent-123"
        valid_request.domain = "chemistry"  # Different from parent's biology domain

        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_ontology_repository.get_by_id.return_value = sample_ontology_version

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is False
        assert "same domain" in response.error_message

    @pytest.mark.asyncio
    async def test_create_ontology_parse_error(self, use_case, valid_request,
                                             mock_ontology_repository, mock_ontology_parser,
                                             mock_subscription_service):
        """Test ontology content parse error."""
        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_ontology_parser.parse_content.side_effect = Exception("Invalid OWL syntax")

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is False
        assert "Failed to parse ontology content" in response.error_message

    @pytest.mark.asyncio
    async def test_create_ontology_validation_failed(self, use_case, valid_request, sample_axioms,
                                                   mock_ontology_repository, mock_ontology_validator,
                                                   mock_ontology_parser, mock_subscription_service):
        """Test ontology validation failure."""
        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_ontology_parser.parse_content.return_value = sample_axioms
        mock_ontology_validator.validate.return_value = ValidationReport(
            is_consistent=False,
            unsat_classes=["UnsatisfiableClass"],
            repair_suggestions=["Remove conflicting axiom"],
            tenant_id="tenant-123",
            ontology_version_id="test-id"
        )

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is False
        assert "Ontology validation failed" in response.error_message
        assert "UnsatisfiableClass" in response.error_message

    @pytest.mark.asyncio
    async def test_create_ontology_repository_error(self, use_case, valid_request, sample_axioms,
                                                  sample_ontology_version, mock_ontology_repository,
                                                  mock_ontology_validator, mock_ontology_parser,
                                                  mock_subscription_service):
        """Test repository error handling."""
        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_ontology_parser.parse_content.return_value = sample_axioms
        mock_ontology_validator.validate.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id="tenant-123",
            ontology_version_id=sample_ontology_version.id
        )
        mock_ontology_repository.create.side_effect = Exception("Database error")

        # Execute and verify exception is raised
        with pytest.raises(ApplicationError) as exc_info:
            await use_case.execute(valid_request)

        assert "Failed to create ontology" in str(exc_info.value)
        assert exc_info.value.error_code == "ONTOLOGY_CREATION_FAILED"

    @pytest.mark.asyncio
    async def test_contract_retry_on_failure(
        self,
        use_case,
        mock_ontology_repository,
        mock_axiom_generator,
        mock_contract_adapter,
        mock_ontology_validator,
        mock_subscription_service,
        monkeypatch,
    ):
        """Ensure failing contract triggers re-prompt with CQ."""

        cqs = [{"id": "cq1", "question": "What is a person?"}]
        request = CreateOntologyRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Test Ontology",
            description="A test ontology",
            domain="biology",
            content="",  # content will be generated
            format="owl",
            competency_questions=cqs,
            contract=Contract(),
        )

        mock_subscription_service.check_ontology_limit.return_value = None
        mock_axiom_generator.generate_axioms.return_value = ["Class: Person"]
        mock_contract_adapter.verify.side_effect = [
            (False, [{"cq_id": "cq1"}]),
            (True, []),
        ]
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_ontology_validator.validate.return_value = ValidationReport(
            tenant_id="tenant-123",
            is_consistent=True,
            violated_rules=[],
            unsat_classes=[],
            repair_suggestions=[],
            explanation=None,
            ontology_version_id="ont1",
        )

        def fake_create(*, tenant_id, domain, axioms):
            obj = Mock()
            obj.id = "ont1"
            obj.domain = domain
            obj.parent_version = None
            obj.tenant_id = tenant_id
            obj.created_at = datetime.utcnow()
            obj.checksum = "chk"
            obj.axioms = axioms
            obj.metadata = {}
            return obj

        monkeypatch.setattr(OntologyVersion, "create", staticmethod(fake_create), raising=False)
        monkeypatch.setattr(
            OntologyVersion,
            "create_child_version",
            staticmethod(
                lambda parent, axioms: fake_create(
                    tenant_id=parent.tenant_id, domain=parent.domain, axioms=axioms
                )
            ),
            raising=False,
        )

        mock_ontology_repository.create.return_value = fake_create(
            tenant_id="tenant-123", domain=ScientificDomain.BIOLOGY, axioms=["Class: Person"]
        )

        response = await use_case.execute(request)

        assert response.success is True
        assert mock_axiom_generator.generate_axioms.call_count == 2
        assert mock_contract_adapter.verify.call_count == 2
        created_ontology = mock_ontology_repository.create.call_args[0][0]
        assert created_ontology.metadata.get("competency_question_ids") == ["cq1"]

    def test_validate_request_none(self, use_case):
        """Test validation with None request."""
        with pytest.raises(ValidationError) as exc_info:
            use_case.validate_request(None)

        assert "Request cannot be None" in str(exc_info.value)