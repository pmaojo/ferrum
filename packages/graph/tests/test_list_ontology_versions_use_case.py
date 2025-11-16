"""Tests for ListOntologyVersionsUseCase."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from domain.entities import OntologyVersion, ScientificDomain
from application.exceptions import (
    ValidationError,
    AuthorizationError,
    ApplicationError
)
from application.use_cases.ontology.list_ontology_versions_use_case import (
    ListOntologyVersionsUseCase,
    ListOntologyVersionsByNameUseCase,
    ListOntologyVersionsResponse,
    ExtendedOntologyRepositoryPort
)
from application.use_cases.ontology.update_ontology_use_case import AuthorizationServicePort
from application.use_cases.dto import (
    ListOntologyVersionsRequestDTO,
    OntologyVersionDTO,
    PaginationParams,
    PaginatedResponse
)
from application.ports import TracingPort


class TestListOntologyVersionsUseCase:
    """Test cases for ListOntologyVersionsUseCase."""

    @pytest.fixture
    def mock_ontology_repository(self):
        """Mock extended ontology repository."""
        repo = Mock(spec=ExtendedOntologyRepositoryPort)
        repo.get_version_name.return_value = "Biology Ontology"
        return repo

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
    def use_case(self, mock_ontology_repository, mock_authorization_service, mock_tracer):
        """Create use case instance with mocked dependencies."""
        return ListOntologyVersionsUseCase(
            ontology_repository=mock_ontology_repository,
            authorization_service=mock_authorization_service,
            tracer=mock_tracer
        )

    @pytest.fixture
    def by_name_use_case(self, mock_ontology_repository, mock_authorization_service, mock_tracer):
        """Create by-name use case instance with mocked dependencies."""
        return ListOntologyVersionsByNameUseCase(
            ontology_repository=mock_ontology_repository,
            authorization_service=mock_authorization_service,
            tracer=mock_tracer
        )

    @pytest.fixture
    def valid_request(self):
        """Valid list ontology versions request."""
        return ListOntologyVersionsRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456"
        )

    @pytest.fixture
    def valid_request_with_filters(self):
        """Valid list ontology versions request with filters."""
        return ListOntologyVersionsRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            ontology_name="Biology Ontology",
            domain="biology",
            pagination=PaginationParams(page=1, page_size=10)
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
    def sample_ontology_versions(self, sample_axioms):
        """Sample ontology versions for testing."""
        base_time = datetime.utcnow()

        # Create parent version
        parent_version = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=sample_axioms
        )
        parent_version.created_at = base_time - timedelta(days=2)

        # Create child version
        child_axioms = sample_axioms + ["Class: Plant"]
        child_version = OntologyVersion.create_child_version(
            parent=parent_version,
            axioms=child_axioms
        )
        child_version.created_at = base_time - timedelta(days=1)

        # Create another independent version
        other_axioms = ["Class: Vehicle", "Class: Car"]
        other_version = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.PHYSICS,
            axioms=other_axioms
        )
        other_version.created_at = base_time

        return [parent_version, child_version, other_version]

    @pytest.mark.asyncio
    async def test_list_ontology_versions_success(self, use_case, valid_request,
                                                sample_ontology_versions,
                                                mock_ontology_repository,
                                                mock_authorization_service):
        """Test successful ontology versions listing."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.list_versions_by_tenant.return_value = (
            sample_ontology_versions, 3
        )

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is True
        assert response.versions is not None
        assert response.versions.total_items == 3
        assert len(response.versions.items) == 3
        assert response.versions.page == 1
        assert response.versions.page_size == 20  # Default page size
        assert response.error_message is None

        # Verify mock calls
        mock_authorization_service.check_permission.assert_called_once_with(
            "user-456", "tenant-123", "read_ontologies"
        )
        mock_ontology_repository.list_versions_by_tenant.assert_called_once_with(
            tenant_id="tenant-123",
            ontology_name=None,
            domain=None,
            page=1,
            page_size=20
        )

        # Verify DTOs are created correctly
        version_dto = response.versions.items[0]
        assert isinstance(version_dto, OntologyVersionDTO)
        assert version_dto.tenant_id == "tenant-123"
        assert version_dto.domain in ["biology", "physics"]
        assert version_dto.axiom_count > 0

    @pytest.mark.asyncio
    async def test_list_ontology_versions_with_filters(self, use_case, valid_request_with_filters,
                                                     sample_ontology_versions,
                                                     mock_ontology_repository,
                                                     mock_authorization_service):
        """Test ontology versions listing with filters."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        # Return only biology versions
        biology_versions = [v for v in sample_ontology_versions if v.domain == ScientificDomain.BIOLOGY]
        mock_ontology_repository.list_versions_by_tenant.return_value = (
            biology_versions, 2
        )

        # Execute
        response = await use_case.execute(valid_request_with_filters)

        # Verify
        assert response.success is True
        assert response.versions is not None
        assert response.versions.total_items == 2
        assert len(response.versions.items) == 2
        assert response.versions.page == 1
        assert response.versions.page_size == 10

        # Verify filters were applied
        mock_ontology_repository.list_versions_by_tenant.assert_called_once_with(
            tenant_id="tenant-123",
            ontology_name="Biology Ontology",
            domain=ScientificDomain.BIOLOGY,
            page=1,
            page_size=10
        )

        # Verify all returned versions are biology domain
        for version_dto in response.versions.items:
            assert version_dto.domain == "biology"

    @pytest.mark.asyncio
    async def test_list_ontology_versions_empty_result(self, use_case, valid_request,
                                                     mock_ontology_repository,
                                                     mock_authorization_service):
        """Test ontology versions listing with empty result."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.list_versions_by_tenant.return_value = ([], 0)

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is True
        assert response.versions is not None
        assert response.versions.total_items == 0
        assert len(response.versions.items) == 0
        assert response.versions.total_pages == 0
        assert response.versions.has_next_page is False
        assert response.versions.has_previous_page is False

    @pytest.mark.asyncio
    async def test_list_ontology_versions_pagination(self, use_case, valid_request,
                                                   sample_ontology_versions,
                                                   mock_ontology_repository,
                                                   mock_authorization_service):
        """Test ontology versions listing with pagination."""
        # Setup request with pagination
        valid_request.pagination = PaginationParams(page=2, page_size=1)

        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.list_versions_by_tenant.return_value = (
            [sample_ontology_versions[1]], 3  # Return second item, total 3
        )

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is True
        assert response.versions is not None
        assert response.versions.total_items == 3
        assert len(response.versions.items) == 1
        assert response.versions.page == 2
        assert response.versions.page_size == 1
        assert response.versions.total_pages == 3
        assert response.versions.has_next_page is True
        assert response.versions.has_previous_page is True

    @pytest.mark.asyncio
    async def test_list_ontology_versions_validation_errors(self, use_case):
        """Test validation errors for invalid requests."""
        test_cases = [
            # Missing tenant_id
            {
                "request": ListOntologyVersionsRequestDTO(
                    tenant_id="",
                    user_id="user-456"
                ),
                "expected_field": "tenant_id"
            },
            # Missing user_id
            {
                "request": ListOntologyVersionsRequestDTO(
                    tenant_id="tenant-123",
                    user_id=""
                ),
                "expected_field": "user_id"
            },
            # Invalid domain
            {
                "request": ListOntologyVersionsRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    domain="invalid_domain"
                ),
                "expected_field": "domain"
            },
            # Empty ontology name if provided
            {
                "request": ListOntologyVersionsRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    ontology_name=""
                ),
                "expected_field": "ontology_name"
            },
            # Ontology name too long
            {
                "request": ListOntologyVersionsRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    ontology_name="x" * 256
                ),
                "expected_field": "ontology_name"
            }
        ]

        for test_case in test_cases:
            with pytest.raises(ValidationError) as exc_info:
                await use_case.execute(test_case["request"])

            assert exc_info.value.field == test_case["expected_field"]

    @pytest.mark.asyncio
    async def test_list_ontology_versions_invalid_pagination_page(self, use_case, valid_request):
        """Test validation error when pagination page is invalid."""
        valid_request.pagination = PaginationParams(page=1, page_size=20)
        valid_request.pagination.page = 0

        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(valid_request)

        assert exc_info.value.field == "pagination.page"
        assert "Page must be greater than or equal to 1" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_ontology_versions_invalid_pagination_page_size(self, use_case, valid_request):
        """Test validation error when pagination page size is invalid."""
        valid_request.pagination = PaginationParams(page=1, page_size=20)
        valid_request.pagination.page_size = 101

        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(valid_request)

        assert exc_info.value.field == "pagination.page_size"
        assert "Page size must be between 1 and 100" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_ontology_versions_authorization_error(self, use_case, valid_request,
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
    async def test_list_ontology_versions_repository_error(self, use_case, valid_request,
                                                         mock_ontology_repository,
                                                         mock_authorization_service):
        """Test repository error handling."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.list_versions_by_tenant.side_effect = Exception("Database error")

        # Execute and verify exception is raised
        with pytest.raises(ApplicationError) as exc_info:
            await use_case.execute(valid_request)

        assert "Failed to list ontology versions" in str(exc_info.value)
        assert exc_info.value.error_code == "ONTOLOGY_VERSIONS_LISTING_FAILED"

    def test_validate_request_none(self, use_case):
        """Test validation with None request."""
        with pytest.raises(ValidationError) as exc_info:
            use_case.validate_request(None)

        assert "Request cannot be None" in str(exc_info.value)


class TestListOntologyVersionsByNameUseCase:
    """Test cases for ListOntologyVersionsByNameUseCase."""

    @pytest.fixture
    def mock_ontology_repository(self):
        """Mock extended ontology repository."""
        return Mock(spec=ExtendedOntologyRepositoryPort)

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
    def by_name_use_case(self, mock_ontology_repository, mock_authorization_service, mock_tracer):
        """Create by-name use case instance with mocked dependencies."""
        return ListOntologyVersionsByNameUseCase(
            ontology_repository=mock_ontology_repository,
            authorization_service=mock_authorization_service,
            tracer=mock_tracer
        )

    @pytest.fixture
    def valid_request_with_name(self):
        """Valid list ontology versions request with name."""
        return ListOntologyVersionsRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            ontology_name="Biology Ontology"
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
    def version_history(self, sample_axioms):
        """Sample version history for testing."""
        base_time = datetime.utcnow()

        # Create version history (parent -> child -> grandchild)
        parent_version = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=sample_axioms
        )
        parent_version.created_at = base_time - timedelta(days=3)

        child_axioms = sample_axioms + ["Class: Plant"]
        child_version = OntologyVersion.create_child_version(
            parent=parent_version,
            axioms=child_axioms
        )
        child_version.created_at = base_time - timedelta(days=2)

        grandchild_axioms = child_axioms + ["Class: Tree"]
        grandchild_version = OntologyVersion.create_child_version(
            parent=child_version,
            axioms=grandchild_axioms
        )
        grandchild_version.created_at = base_time - timedelta(days=1)

        return [parent_version, child_version, grandchild_version]

    @pytest.mark.asyncio
    async def test_list_ontology_versions_by_name_success(self, by_name_use_case,
                                                        valid_request_with_name,
                                                        version_history,
                                                        mock_ontology_repository,
                                                        mock_authorization_service):
        """Test successful ontology version history listing by name."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.list_versions.return_value = version_history

        # Execute
        response = await by_name_use_case.execute(valid_request_with_name)

        # Verify
        assert response.success is True
        assert response.versions is not None
        assert response.versions.total_items == 3
        assert len(response.versions.items) == 3

        # Verify versions are sorted by creation date (newest first)
        # The first item should be the latest (grandchild)
        assert response.versions.items[0].is_latest is True
        assert response.versions.items[1].is_latest is False
        assert response.versions.items[2].is_latest is False

        # Verify mock calls
        mock_authorization_service.check_permission.assert_called_once_with(
            "user-456", "tenant-123", "read_ontologies"
        )
        mock_ontology_repository.list_versions.assert_called_once_with(
            name="Biology Ontology",
            tenant_id="tenant-123"
        )

    @pytest.mark.asyncio
    async def test_list_ontology_versions_by_name_validation_error(self, by_name_use_case):
        """Test validation error when ontology name is missing."""
        request = ListOntologyVersionsRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456"
            # Missing ontology_name
        )

        with pytest.raises(ValidationError) as exc_info:
            await by_name_use_case.execute(request)

        assert exc_info.value.field == "ontology_name"
        assert "required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_ontology_versions_by_name_empty_result(self, by_name_use_case,
                                                             valid_request_with_name,
                                                             mock_ontology_repository,
                                                             mock_authorization_service):
        """Test version history listing with empty result."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.list_versions.return_value = []

        # Execute
        response = await by_name_use_case.execute(valid_request_with_name)

        # Verify
        assert response.success is True
        assert response.versions is not None
        assert response.versions.total_items == 0
        assert len(response.versions.items) == 0

    @pytest.mark.asyncio
    async def test_list_ontology_versions_by_name_pagination(self, by_name_use_case,
                                                           valid_request_with_name,
                                                           version_history,
                                                           mock_ontology_repository,
                                                           mock_authorization_service):
        """Test version history listing with pagination."""
        # Setup request with pagination
        valid_request_with_name.pagination = PaginationParams(page=2, page_size=1)

        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.list_versions.return_value = version_history

        # Execute
        response = await by_name_use_case.execute(valid_request_with_name)

        # Verify
        assert response.success is True
        assert response.versions is not None
        assert response.versions.total_items == 3
        assert len(response.versions.items) == 1  # Only one item per page
        assert response.versions.page == 2
        assert response.versions.page_size == 1
        assert response.versions.total_pages == 3
        assert response.versions.has_next_page is True
        assert response.versions.has_previous_page is True

        # The second page should contain the second newest version
        assert response.versions.items[0].is_latest is False
