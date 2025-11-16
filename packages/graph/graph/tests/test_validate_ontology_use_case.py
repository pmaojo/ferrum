"""Tests for ValidateOntologyUseCase."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from typing import List, Optional

from domain.entities import OntologyVersion, ScientificDomain, ValidationReport, Triple
from application.exceptions import (
    ValidationError,
    NotFoundError,
    AuthorizationError,
    ApplicationError
)
from application.use_cases.ontology.validate_ontology_use_case import (
    ValidateOntologyUseCase,
    ValidateOntologyConsistencyUseCase,
    ValidateOntologyResponse
)
from application.use_cases.ontology.create_ontology_use_case import OntologyRepositoryPort
from application.use_cases.ontology.update_ontology_use_case import AuthorizationServicePort
from application.use_cases.dto import ValidateOntologyRequestDTO, OntologyValidationResultDTO
from application.ports import OntologyValidatorPort, TracingPort


class TestValidateOntologyUseCase:
    """Test cases for ValidateOntologyUseCase."""

    @pytest.fixture
    def mock_ontology_repository(self):
        """Mock ontology repository."""
        return Mock(spec=OntologyRepositoryPort)

    @pytest.fixture
    def mock_ontology_validator(self):
        """Mock ontology validator."""
        return Mock(spec=OntologyValidatorPort)

    @pytest.fixture
    def mock_authorization_service(self):
        """Mock authorization service."""
        return Mock(spec=AuthorizationServicePort)

    @pytest.fixture
    def mock_tracer(self):
        """Mock tracer."""
        tracer = Mock(spec=TracingPort)
        tracer.start_span.return_value.__enter__ = Mock()
        tracer.start_span.return_value.__exit__ = Mock()
        return tracer

    @pytest.fixture
    def use_case(self, mock_ontology_repository, mock_ontology_validator,
                 mock_authorization_service, mock_tracer):
        """Create use case instance with mocked dependencies."""
        return ValidateOntologyUseCase(
            ontology_repository=mock_ontology_repository,
            ontology_validator=mock_ontology_validator,
            authorization_service=mock_authorization_service,
            tracer=mock_tracer
        )

    @pytest.fixture
    def consistency_use_case(self, mock_ontology_repository, mock_ontology_validator,
                           mock_authorization_service, mock_tracer):
        """Create consistency use case instance with mocked dependencies."""
        return ValidateOntologyConsistencyUseCase(
            ontology_repository=mock_ontology_repository,
            ontology_validator=mock_ontology_validator,
            authorization_service=mock_authorization_service,
            tracer=mock_tracer
        )

    @pytest.fixture
    def valid_request(self):
        """Valid validate ontology request."""
        return ValidateOntologyRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            ontology_version_id="ontology-version-789"
        )

    @pytest.fixture
    def valid_request_with_triples(self):
        """Valid validate ontology request with triples."""
        return ValidateOntologyRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            ontology_version_id="ontology-version-789",
            triples=[
                {
                    "subject": "Person:John",
                    "predicate": "hasParent",
                    "object": "Person:Mary"
                },
                {
                    "subject": "Person:Mary",
                    "predicate": "rdf:type",
                    "object": "Person"
                }
            ]
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
    async def test_validate_ontology_success_consistent(self, use_case, valid_request,
                                                      sample_ontology_version,
                                                      mock_ontology_repository,
                                                      mock_ontology_validator,
                                                      mock_authorization_service):
        """Test successful ontology validation with consistent result."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.return_value = sample_ontology_version
        mock_ontology_validator.validate.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id="tenant-123",
            ontology_version_id="ontology-version-789"
        )

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is True
        assert response.validation_result is not None
        assert response.validation_result.is_consistent is True
        assert response.validation_result.unsat_classes == []
        assert response.validation_result.repair_suggestions == []
        assert response.validation_result.validation_errors == []
        assert response.error_message is None

        # Verify mock calls
        mock_authorization_service.check_permission.assert_called_once_with(
            "user-456", "ontology-version-789", "read"
        )
        mock_ontology_repository.get_by_id.assert_called_once_with(
            "ontology-version-789", "tenant-123"
        )
        mock_ontology_validator.validate.assert_called_once_with(
            triples=[], ontology_version_id="ontology-version-789"
        )

    @pytest.mark.asyncio
    async def test_validate_ontology_success_inconsistent(self, use_case, valid_request,
                                                        sample_ontology_version,
                                                        mock_ontology_repository,
                                                        mock_ontology_validator,
                                                        mock_authorization_service):
        """Test successful ontology validation with inconsistent result."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.return_value = sample_ontology_version
        mock_ontology_validator.validate.return_value = ValidationReport(
            is_consistent=False,
            unsat_classes=["UnsatisfiableClass", "ConflictingClass"],
            repair_suggestions=["Remove conflicting axiom", "Add disjoint declaration"],
            tenant_id="tenant-123",
            ontology_version_id="ontology-version-789"
        )

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is True
        assert response.validation_result is not None
        assert response.validation_result.is_consistent is False
        assert response.validation_result.unsat_classes == ["UnsatisfiableClass", "ConflictingClass"]
        assert response.validation_result.repair_suggestions == ["Remove conflicting axiom", "Add disjoint declaration"]
        assert len(response.validation_result.validation_errors) == 2
        assert "Unsatisfiable class: UnsatisfiableClass" in response.validation_result.validation_errors
        assert "Unsatisfiable class: ConflictingClass" in response.validation_result.validation_errors
        assert response.error_message is None

    @pytest.mark.asyncio
    async def test_validate_ontology_with_triples_success(self, use_case, valid_request_with_triples,
                                                        sample_ontology_version,
                                                        mock_ontology_repository,
                                                        mock_ontology_validator,
                                                        mock_authorization_service):
        """Test successful ontology validation with triples."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.return_value = sample_ontology_version
        mock_ontology_validator.validate.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id="tenant-123",
            ontology_version_id="ontology-version-789"
        )

        # Execute
        response = await use_case.execute(valid_request_with_triples)

        # Verify
        assert response.success is True
        assert response.validation_result.is_consistent is True

        # Verify triples were passed to validator
        call_args = mock_ontology_validator.validate.call_args
        triples = call_args[1]["triples"]
        assert len(triples) == 2
        assert all(isinstance(triple, Triple) for triple in triples)
        assert triples[0].subject == "Person:John"
        assert triples[0].predicate == "hasParent"
        assert triples[0].object == "Person:Mary"
        assert triples[0].tenant_id == "tenant-123"

    @pytest.mark.asyncio
    async def test_validate_ontology_validation_errors(self, use_case):
        """Test validation errors for invalid requests."""
        test_cases = [
            # Missing tenant_id
            {
                "request": ValidateOntologyRequestDTO(
                    tenant_id="",
                    user_id="user-456",
                    ontology_version_id="ontology-version-789"
                ),
                "expected_field": "tenant_id"
            },
            # Missing user_id
            {
                "request": ValidateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="",
                    ontology_version_id="ontology-version-789"
                ),
                "expected_field": "user_id"
            },
            # Missing ontology_version_id
            {
                "request": ValidateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    ontology_version_id=""
                ),
                "expected_field": "ontology_version_id"
            },
            # Invalid triples format - not a list
            {
                "request": ValidateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    ontology_version_id="ontology-version-789",
                    triples="not a list"
                ),
                "expected_field": "triples"
            },
            # Invalid triple - not a dict
            {
                "request": ValidateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    ontology_version_id="ontology-version-789",
                    triples=["not a dict"]
                ),
                "expected_field": "triples"
            },
            # Invalid triple - missing subject
            {
                "request": ValidateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    ontology_version_id="ontology-version-789",
                    triples=[{"predicate": "hasParent", "object": "Person:Mary"}]
                ),
                "expected_field": "triples"
            },
            # Invalid triple - empty subject
            {
                "request": ValidateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    ontology_version_id="ontology-version-789",
                    triples=[{"subject": "", "predicate": "hasParent", "object": "Person:Mary"}]
                ),
                "expected_field": "triples"
            }
        ]

        for test_case in test_cases:
            with pytest.raises(ValidationError) as exc_info:
                await use_case.execute(test_case["request"])

            assert exc_info.value.field == test_case["expected_field"]

    @pytest.mark.asyncio
    async def test_validate_ontology_authorization_error(self, use_case, valid_request,
                                                       mock_authorization_service):
        """Test authorization error."""
        # Setup mock to raise authorization error
        mock_authorization_service.check_permission.side_effect = AuthorizationError(
            message="User not authorized",
            user_id="user-456"
        )

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is False
        assert "User not authorized" in response.error_message

    @pytest.mark.asyncio
    async def test_validate_ontology_not_found(self, use_case, valid_request,
                                             mock_ontology_repository,
                                             mock_authorization_service):
        """Test ontology version not found error."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.return_value = None

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is False
        assert "not found" in response.error_message

    @pytest.mark.asyncio
    async def test_validate_ontology_validator_error(self, use_case, valid_request,
                                                   sample_ontology_version,
                                                   mock_ontology_repository,
                                                   mock_authorization_service,
                                                   mock_ontology_validator):
        """Test ontology validator error handling."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.return_value = sample_ontology_version
        mock_ontology_validator.validate.side_effect = Exception("Validator error")

        # Execute and verify exception is raised
        with pytest.raises(ApplicationError) as exc_info:
            await use_case.execute(valid_request)

        assert "Failed to validate ontology" in str(exc_info.value)
        assert exc_info.value.error_code == "ONTOLOGY_VALIDATION_FAILED"

    def test_validate_request_none(self, use_case):
        """Test validation with None request."""
        with pytest.raises(ValidationError) as exc_info:
            use_case.validate_request(None)

        assert "Request cannot be None" in str(exc_info.value)


class TestValidateOntologyConsistencyUseCase:
    """Test cases for ValidateOntologyConsistencyUseCase."""

    @pytest.fixture
    def mock_ontology_repository(self):
        """Mock ontology repository."""
        return Mock(spec=OntologyRepositoryPort)

    @pytest.fixture
    def mock_ontology_validator(self):
        """Mock ontology validator."""
        return Mock(spec=OntologyValidatorPort)

    @pytest.fixture
    def mock_authorization_service(self):
        """Mock authorization service."""
        return Mock(spec=AuthorizationServicePort)

    @pytest.fixture
    def mock_tracer(self):
        """Mock tracer."""
        tracer = Mock(spec=TracingPort)
        tracer.start_span.return_value.__enter__ = Mock()
        tracer.start_span.return_value.__exit__ = Mock()
        return tracer

    @pytest.fixture
    def consistency_use_case(self, mock_ontology_repository, mock_ontology_validator,
                           mock_authorization_service, mock_tracer):
        """Create consistency use case instance with mocked dependencies."""
        return ValidateOntologyConsistencyUseCase(
            ontology_repository=mock_ontology_repository,
            ontology_validator=mock_ontology_validator,
            authorization_service=mock_authorization_service,
            tracer=mock_tracer
        )

    @pytest.fixture
    def valid_request(self):
        """Valid validate ontology request."""
        return ValidateOntologyRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            ontology_version_id="ontology-version-789"
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
    async def test_validate_ontology_consistency_success_consistent(self, consistency_use_case,
                                                                  valid_request,
                                                                  sample_ontology_version,
                                                                  mock_ontology_repository,
                                                                  mock_ontology_validator,
                                                                  mock_authorization_service):
        """Test successful ontology consistency validation with consistent result."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.return_value = sample_ontology_version
        mock_ontology_validator.validate.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id="tenant-123",
            ontology_version_id="ontology-version-789"
        )

        # Execute
        response = await consistency_use_case.execute(valid_request)

        # Verify
        assert response.success is True
        assert response.validation_result is not None
        assert response.validation_result.is_consistent is True
        assert response.validation_result.unsat_classes == []
        assert response.validation_result.repair_suggestions == []
        assert response.validation_result.validation_errors == []
        assert response.error_message is None

        # Verify that empty triples were passed (ontology-only validation)
        mock_ontology_validator.validate.assert_called_once_with(
            triples=[], ontology_version_id="ontology-version-789"
        )

    @pytest.mark.asyncio
    async def test_validate_ontology_consistency_success_inconsistent(self, consistency_use_case,
                                                                    valid_request,
                                                                    sample_ontology_version,
                                                                    mock_ontology_repository,
                                                                    mock_ontology_validator,
                                                                    mock_authorization_service):
        """Test successful ontology consistency validation with inconsistent result."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.return_value = sample_ontology_version
        mock_ontology_validator.validate.return_value = ValidationReport(
            is_consistent=False,
            unsat_classes=["UnsatisfiableClass"],
            repair_suggestions=["Remove conflicting axiom"],
            tenant_id="tenant-123",
            ontology_version_id="ontology-version-789"
        )

        # Execute
        response = await consistency_use_case.execute(valid_request)

        # Verify
        assert response.success is True
        assert response.validation_result is not None
        assert response.validation_result.is_consistent is False
        assert response.validation_result.unsat_classes == ["UnsatisfiableClass"]
        assert response.validation_result.repair_suggestions == ["Remove conflicting axiom"]
        assert len(response.validation_result.validation_errors) == 2
        assert "Inconsistent ontology: UnsatisfiableClass" in response.validation_result.validation_errors
        assert "Ontology contains contradictory axioms" in response.validation_result.validation_errors
        assert response.error_message is None