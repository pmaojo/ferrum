"""Tests for AuditUserActivityUseCase."""

import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta

from domain.entities import User, UserRole, Organization, SubscriptionTier
from application.exceptions import (
    ValidationError,
    NotFoundError,
    AuthorizationError
)
from application.use_cases.user_org.audit_user_activity_use_case import AuditUserActivityUseCase, AuditUserActivityResponse
from application.use_cases.dto import AuditUserActivityRequestDTO, UserActivityDTO, PaginationParams


class TestAuditUserActivityUseCase:
    """Test cases for AuditUserActivityUseCase."""

    @pytest.fixture
    def mock_user_repository(self):
        """Mock user repository."""
        return Mock()

    @pytest.fixture
    def mock_organization_repository(self):
        """Mock organization repository."""
        return Mock()

    @pytest.fixture
    def mock_authorization_service(self):
        """Mock authorization service."""
        return Mock()

    @pytest.fixture
    def mock_audit_service(self):
        """Mock audit service."""
        return Mock()

    @pytest.fixture
    def mock_tracer(self):
        """Mock tracer."""
        mock_tracer = Mock()
        mock_span = Mock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=None)
        mock_tracer.start_span.return_value = mock_span
        return mock_tracer

    @pytest.fixture
    def use_case(
        self,
        mock_user_repository,
        mock_organization_repository,
        mock_authorization_service,
        mock_audit_service,
        mock_tracer
    ):
        """Create use case instance with mocked dependencies."""
        return AuditUserActivityUseCase(
            user_repository=mock_user_repository,
            organization_repository=mock_organization_repository,
            authorization_service=mock_authorization_service,
            audit_service=mock_audit_service,
            tracer=mock_tracer
        )

    @pytest.fixture
    def valid_request(self):
        """Valid audit user activity request."""
        return AuditUserActivityRequestDTO(
            organization_id="org-123",
            requesting_user_id="admin-123",
            pagination=PaginationParams(page=1, page_size=20)
        )

    @pytest.fixture
    def specific_user_request(self):
        """Request for specific user activity."""
        return AuditUserActivityRequestDTO(
            user_id="user-123",
            organization_id="org-123",
            requesting_user_id="admin-123",
            pagination=PaginationParams(page=1, page_size=10)
        )

    @pytest.fixture
    def mock_organization(self):
        """Mock organization entity."""
        return Organization(
            id="org-123",
            name="Test Organization",
            subscription_tier=SubscriptionTier.FREE,
            subscription_expires_at=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True
        )

    @pytest.fixture
    def mock_admin_user(self):
        """Mock admin user entity."""
        return User(
            id="admin-123",
            email="admin@example.com",
            name="Admin User",
            password_hash="hashed_password",
            organization_id="org-123",
            role=UserRole.ADMIN,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_login=None,
            is_active=True
        )

    @pytest.fixture
    def mock_target_user(self):
        """Mock target user entity."""
        return User(
            id="user-123",
            email="user@example.com",
            name="Test User",
            password_hash="hashed_password",
            organization_id="org-123",
            role=UserRole.EDITOR,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_login=None,
            is_active=True
        )

    @pytest.fixture
    def mock_activity_records(self):
        """Mock activity records."""
        now = datetime.utcnow()
        return [
            {
                "id": "activity-1",
                "user_id": "user-123",
                "activity_type": "user_login",
                "description": "User logged in",
                "resource_id": None,
                "resource_type": None,
                "metadata": {"ip_address": "192.168.1.1"},
                "timestamp": now - timedelta(hours=1)
            },
            {
                "id": "activity-2",
                "user_id": "user-123",
                "activity_type": "knowledge_graph_created",
                "description": "Created knowledge graph 'Test KG'",
                "resource_id": "kg-456",
                "resource_type": "knowledge_graph",
                "metadata": {"kg_name": "Test KG"},
                "timestamp": now - timedelta(hours=2)
            }
        ]

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_audit_organization_activity_success(
        self,
        use_case,
        valid_request,
        mock_organization,
        mock_admin_user,
        mock_activity_records,
        mock_organization_repository,
        mock_user_repository,
        mock_authorization_service,
        mock_audit_service
    ):
        """Test successful organization activity audit."""
        # Arrange
        mock_organization_repository.get_by_id.return_value = mock_organization
        mock_user_repository.get_by_id.return_value = mock_admin_user
        mock_authorization_service.check_permission.return_value = None
        mock_audit_service.get_user_activity.return_value = (mock_activity_records, 2)

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is True
        assert response.activities is not None
        assert len(response.activities.items) == 2
        assert response.activities.total_items == 2
        assert response.activities.page == 1
        assert response.activities.page_size == 20

        # Verify method calls
        mock_organization_repository.get_by_id.assert_called_once_with("org-123")
        mock_user_repository.get_by_id.assert_called_once_with("admin-123")
        mock_authorization_service.check_permission.assert_called_once_with(
            user_id="admin-123",
            resource_id="org-123",
            action="view_audit_logs"
        )
        mock_audit_service.get_user_activity.assert_called_once_with(
            user_id=None,
            organization_id="org-123",
            start_date=None,
            end_date=None,
            activity_types=None,
            page=1,
            page_size=20
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_audit_specific_user_activity_success(
        self,
        use_case,
        specific_user_request,
        mock_organization,
        mock_admin_user,
        mock_target_user,
        mock_activity_records,
        mock_organization_repository,
        mock_user_repository,
        mock_authorization_service,
        mock_audit_service
    ):
        """Test successful specific user activity audit."""
        # Arrange
        mock_organization_repository.get_by_id.return_value = mock_organization
        mock_user_repository.get_by_id.side_effect = lambda user_id: {
            "admin-123": mock_admin_user,
            "user-123": mock_target_user
        }.get(user_id)
        mock_authorization_service.check_permission.return_value = None
        mock_audit_service.get_user_activity.return_value = (mock_activity_records, 2)

        # Act
        response = await use_case.execute(specific_user_request)

        # Assert
        assert response.success is True
        assert response.activities is not None
        assert len(response.activities.items) == 2
        assert response.activities.page_size == 10

        # Verify specific user was requested
        mock_audit_service.get_user_activity.assert_called_once_with(
            user_id="user-123",
            organization_id="org-123",
            start_date=None,
            end_date=None,
            activity_types=None,
            page=1,
            page_size=10
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_audit_activity_with_date_filter(
        self,
        use_case,
        mock_organization,
        mock_admin_user,
        mock_activity_records,
        mock_organization_repository,
        mock_user_repository,
        mock_authorization_service,
        mock_audit_service
    ):
        """Test activity audit with date filtering."""
        # Arrange
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        request = AuditUserActivityRequestDTO(
            organization_id="org-123",
            requesting_user_id="admin-123",
            start_date=start_date,
            end_date=end_date,
            pagination=PaginationParams(page=1, page_size=20)
        )

        mock_organization_repository.get_by_id.return_value = mock_organization
        mock_user_repository.get_by_id.return_value = mock_admin_user
        mock_authorization_service.check_permission.return_value = None
        mock_audit_service.get_user_activity.return_value = (mock_activity_records, 2)

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is True

        # Verify date filters were passed
        mock_audit_service.get_user_activity.assert_called_once_with(
            user_id=None,
            organization_id="org-123",
            start_date=start_date,
            end_date=end_date,
            activity_types=None,
            page=1,
            page_size=20
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_audit_activity_with_activity_types_filter(
        self,
        use_case,
        mock_organization,
        mock_admin_user,
        mock_activity_records,
        mock_organization_repository,
        mock_user_repository,
        mock_authorization_service,
        mock_audit_service
    ):
        """Test activity audit with activity types filtering."""
        # Arrange
        request = AuditUserActivityRequestDTO(
            organization_id="org-123",
            requesting_user_id="admin-123",
            activity_types=["user_login", "user_logout"],
            pagination=PaginationParams(page=1, page_size=20)
        )

        mock_organization_repository.get_by_id.return_value = mock_organization
        mock_user_repository.get_by_id.return_value = mock_admin_user
        mock_authorization_service.check_permission.return_value = None
        mock_audit_service.get_user_activity.return_value = (mock_activity_records, 2)

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is True

        # Verify activity types filter was passed
        mock_audit_service.get_user_activity.assert_called_once_with(
            user_id=None,
            organization_id="org-123",
            start_date=None,
            end_date=None,
            activity_types=["user_login", "user_logout"],
            page=1,
            page_size=20
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_audit_activity_empty_organization_id(self, use_case):
        """Test audit with empty organization ID."""
        # Arrange
        request = AuditUserActivityRequestDTO(
            organization_id="",
            requesting_user_id="admin-123"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Organization ID is required and cannot be empty" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_audit_activity_empty_requesting_user_id(self, use_case):
        """Test audit with empty requesting user ID."""
        # Arrange
        request = AuditUserActivityRequestDTO(
            organization_id="org-123",
            requesting_user_id=""
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Requesting user ID is required and cannot be empty" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_audit_activity_invalid_date_range(self, use_case):
        """Test audit with invalid date range."""
        # Arrange
        request = AuditUserActivityRequestDTO(
            organization_id="org-123",
            requesting_user_id="admin-123",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() - timedelta(days=1)  # End before start
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Start date cannot be after end date" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_audit_activity_invalid_pagination(self, use_case):
        """Test audit with invalid pagination."""
        # Arrange
        request = AuditUserActivityRequestDTO(
            organization_id="org-123",
            requesting_user_id="admin-123",
            pagination=PaginationParams(page=0, page_size=20)  # Invalid page
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Page must be greater than or equal to 1" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_audit_activity_organization_not_found(
        self,
        use_case,
        valid_request,
        mock_organization_repository
    ):
        """Test audit when organization doesn't exist."""
        # Arrange
        mock_organization_repository.get_by_id.return_value = None

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "Organization with ID 'org-123' not found" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_audit_activity_requesting_user_not_found(
        self,
        use_case,
        valid_request,
        mock_organization,
        mock_organization_repository,
        mock_user_repository
    ):
        """Test audit when requesting user doesn't exist."""
        # Arrange
        mock_organization_repository.get_by_id.return_value = mock_organization
        mock_user_repository.get_by_id.return_value = None

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "Requesting user with ID 'admin-123' not found" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_audit_activity_authorization_error(
        self,
        use_case,
        valid_request,
        mock_organization,
        mock_admin_user,
        mock_organization_repository,
        mock_user_repository,
        mock_authorization_service
    ):
        """Test audit with authorization error."""
        # Arrange
        mock_organization_repository.get_by_id.return_value = mock_organization
        mock_user_repository.get_by_id.return_value = mock_admin_user
        mock_authorization_service.check_permission.side_effect = AuthorizationError(
            message="User lacks permission to view audit logs",
            user_id="admin-123",
            resource_id="org-123",
            required_permission="view_audit_logs"
        )

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "User lacks permission to view audit logs" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_audit_activity_different_organization(
        self,
        use_case,
        valid_request,
        mock_organization,
        mock_organization_repository,
        mock_user_repository,
        mock_authorization_service
    ):
        """Test audit when requesting user is in different organization."""
        # Arrange
        different_org_user = User(
            id="admin-123",
            email="admin@example.com",
            name="Admin User",
            password_hash="hashed_password",
            organization_id="other-org",  # Different organization
            role=UserRole.ADMIN,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_login=None,
            is_active=True
        )

        mock_organization_repository.get_by_id.return_value = mock_organization
        mock_user_repository.get_by_id.return_value = different_org_user
        mock_authorization_service.check_permission.return_value = None

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "Cannot view audit logs for different organization" in response.error_message