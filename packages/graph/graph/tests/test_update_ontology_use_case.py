"""Tests for UpdateOntologyUseCase."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from typing import List, Optional

from domain.entities import OntologyVersion, ScientificDomain, ValidationReport
from application.exceptions import (
    ValidationError,
    BusinessRuleViolationError,
    NotFoundError,
    AuthorizationError,
    ApplicationError
)
from application.use_cases.ontology.update_ontology_use_case import (
    UpdateOntologyUseCase,
    UpdateOntologyResponse,
    AuthorizationServicePort
)
from application.use_cases.ontology.create_ontology_use_case import (
    OntologyRepositoryPort,
    SubscriptionServicePort,
    OntologyParserPort
)
from application.use_cases.dto import UpdateOntologyRequestDTO, OntologyDTO
from application.ports import OntologyValidatorPort, TracingPort


class TestUpdateOntologyUseCase:
    """Test cases for UpdateOntologyUseCase."""

    @pytest.fixture
    def mock_ontology_repository(self):
        """Mock ontology repository."""
        repo = Mock(spec=OntologyRepositoryPort)
        repo.get_version_name.return_value = "Existing Ontology"
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
                 mock_ontology_parser, mock_subscription_service,
                 mock_authorization_service, mock_tracer):
        """Create use case instance with mocked dependencies."""
        return UpdateOntologyUseCase(
            ontology_repository=mock_ontology_repository,
            ontology_validator=mock_ontology_validator,
            ontology_parser=mock_ontology_parser,
            subscription_service=mock_subscription_service,
            authorization_service=mock_authorization_service,
            tracer=mock_tracer
        )

    @pytest.fixture
    def valid_request(self):
        """Valid update ontology request."""
        return UpdateOntologyRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            ontology_id="ontology-789",
            name="Updated Ontology",
            description="An updated test ontology",
            content="<owl:Ontology>...updated...</owl:Ontology>",
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
    def updated_axioms(self):
        """Updated axioms for testing."""
        return [
            "Class: Person",
            "Class: Animal",
            "Class: Plant",  # New class
            "ObjectProperty: hasParent"
        ]

    @pytest.fixture
    def parent_ontology_version(self, sample_axioms):
        """Parent ontology version for testing."""
        return OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=sample_axioms
        )

    @pytest.mark.asyncio
    async def test_update_ontology_success(self, use_case, valid_request, updated_axioms,
                                         parent_ontology_version, mock_ontology_repository,
                                         mock_ontology_validator, mock_ontology_parser,
                                         mock_subscription_service, mock_authorization_service):
        """Test successful ontology update with new version creation."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.return_value = parent_ontology_version
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_parser.parse_content.return_value = updated_axioms
        mock_ontology_validator.validate_delta.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id="tenant-123",
            ontology_version_id="new-version-id"
        )

        # Create child version for mocking
        child_version = OntologyVersion.create_child_version(
            parent=parent_ontology_version,
            axioms=updated_axioms
        )
        mock_ontology_repository.create.return_value = child_version

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is True
        assert response.ontology is not None
        assert response.ontology.parent_version_id == parent_ontology_version.id
        assert response.ontology.axiom_count == 4  # Updated axioms count
        assert response.error_message is None

        # Verify mock calls
        mock_authorization_service.check_permission.assert_called_once_with(
            "user-456", "ontology-789", "update"
        )
        mock_ontology_repository.get_by_id.assert_called_once_with("ontology-789", "tenant-123")
        mock_subscription_service.check_ontology_limit.assert_called_once_with("tenant-123")
        mock_ontology_parser.parse_content.assert_called_once_with(
            "<owl:Ontology>...updated...</owl:Ontology>", "owl"
        )
        mock_ontology_validator.validate_delta.assert_called_once()
        mock_ontology_repository.create.assert_called_once()
        mock_ontology_repository.set_version_name.assert_called_once_with(
            child_version.id,
            valid_request.name,
            "tenant-123",
        )

    @pytest.mark.asyncio
    async def test_update_ontology_validation_errors(self, use_case):
        """Test validation errors for invalid requests."""
        test_cases = [
            # Missing tenant_id
            {
                "request": UpdateOntologyRequestDTO(
                    tenant_id="",
                    user_id="user-456",
                    ontology_id="ontology-789",
                    content="content"
                ),
                "expected_field": "tenant_id"
            },
            # Missing user_id
            {
                "request": UpdateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="",
                    ontology_id="ontology-789",
                    content="content"
                ),
                "expected_field": "user_id"
            },
            # Missing ontology_id
            {
                "request": UpdateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    ontology_id="",
                    content="content"
                ),
                "expected_field": "ontology_id"
            },
            # No update fields provided
            {
                "request": UpdateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    ontology_id="ontology-789"
                ),
                "expected_field": "update_fields"
            },
            # Empty name if provided
            {
                "request": UpdateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    ontology_id="ontology-789",
                    name=""
                ),
                "expected_field": "name"
            },
            # Name too long
            {
                "request": UpdateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    ontology_id="ontology-789",
                    name="x" * 256
                ),
                "expected_field": "name"
            },
            # Description too long
            {
                "request": UpdateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    ontology_id="ontology-789",
                    description="x" * 1001
                ),
                "expected_field": "description"
            },
            # Empty content if provided
            {
                "request": UpdateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    ontology_id="ontology-789",
                    content=""
                ),
                "expected_field": "content"
            },
            # Invalid format
            {
                "request": UpdateOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    ontology_id="ontology-789",
                    content="content",
                    format="invalid_format"
                ),
                "expected_field": "format"
            }
        ]

        for test_case in test_cases:
            with pytest.raises(ValidationError) as exc_info:
                await use_case.execute(test_case["request"])

            assert exc_info.value.field == test_case["expected_field"]

    @pytest.mark.asyncio
    async def test_update_ontology_authorization_error(self, use_case, valid_request,
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
    async def test_update_ontology_not_found(self, use_case, valid_request,
                                           mock_ontology_repository, mock_authorization_service):
        """Test ontology not found error."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.return_value = None

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is False
        assert "not found" in response.error_message

    @pytest.mark.asyncio
    async def test_update_ontology_subscription_limit_exceeded(self, use_case, valid_request,
                                                             parent_ontology_version,
                                                             mock_ontology_repository,
                                                             mock_authorization_service,
                                                             mock_subscription_service):
        """Test subscription limit exceeded error."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.return_value = parent_ontology_version
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
    async def test_update_ontology_metadata_only_not_supported(self, use_case, parent_ontology_version,
                                                             mock_ontology_repository,
                                                             mock_authorization_service,
                                                             mock_subscription_service):
        """Test that metadata-only updates are not supported."""
        # Create request with only metadata changes (no content)
        request = UpdateOntologyRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            ontology_id="ontology-789",
            name="New Name",
            description="New Description"
        )

        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.return_value = parent_ontology_version
        mock_subscription_service.check_ontology_limit.return_value = None

        # Execute
        response = await use_case.execute(request)

        # Verify
        assert response.success is False
        assert "Only content updates are supported" in response.error_message

    @pytest.mark.asyncio
    async def test_update_ontology_parse_error(self, use_case, valid_request, parent_ontology_version,
                                             mock_ontology_repository, mock_authorization_service,
                                             mock_subscription_service, mock_ontology_parser):
        """Test ontology content parse error."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.return_value = parent_ontology_version
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_parser.parse_content.side_effect = Exception("Invalid OWL syntax")

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is False
        assert "Failed to parse ontology content" in response.error_message

    @pytest.mark.asyncio
    async def test_update_ontology_validation_failed(self, use_case, valid_request, updated_axioms,
                                                   parent_ontology_version, mock_ontology_repository,
                                                   mock_authorization_service, mock_subscription_service,
                                                   mock_ontology_parser, mock_ontology_validator):
        """Test ontology validation failure."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.return_value = parent_ontology_version
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_parser.parse_content.return_value = updated_axioms
        mock_ontology_validator.validate_delta.return_value = ValidationReport(
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
    async def test_update_ontology_repository_error(self, use_case, valid_request, updated_axioms,
                                                  parent_ontology_version, mock_ontology_repository,
                                                  mock_authorization_service, mock_subscription_service,
                                                  mock_ontology_parser, mock_ontology_validator):
        """Test repository error handling."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.return_value = parent_ontology_version
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_parser.parse_content.return_value = updated_axioms
        mock_ontology_validator.validate_delta.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id="tenant-123",
            ontology_version_id="test-id"
        )
        mock_ontology_repository.create.side_effect = Exception("Database error")

        # Execute and verify exception is raised
        with pytest.raises(ApplicationError) as exc_info:
            await use_case.execute(valid_request)

        assert "Failed to update ontology" in str(exc_info.value)
        assert exc_info.value.error_code == "ONTOLOGY_UPDATE_FAILED"

    def test_validate_request_none(self, use_case):
        """Test validation with None request."""
        with pytest.raises(ValidationError) as exc_info:
            use_case.validate_request(None)

        assert "Request cannot be None" in str(exc_info.value)