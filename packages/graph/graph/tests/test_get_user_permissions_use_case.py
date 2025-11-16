"""Tests for GetUserPermissionsUseCase."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from domain.entities import User, UserRole
from application.exceptions import (
    ValidationError,
    NotFoundError,
    AuthorizationError
)
from application.use_cases.user_org.get_user_permissions_use_case import GetUserPermissionsUseCase, GetUserPermissionsResponse
from application.use_cases.dto import GetUserPermissionsRequestDTO, UserPermissionsDTO


class TestGetUserPermissionsUseCase:
    """Test cases for GetUserPermissionsUseCase."""

    @pytest.fixture
    def mock_user_repository(self):
        """Mock user repository."""
        return Mock()

    @pytest.fixture
    def mock_authorization_service(self):
        """Mock authorization service."""
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
        mock_authorization_service,
        mock_tracer
    ):
        """Create use case instance with mocked dependencies."""
        return GetUserPermissionsUseCase(
            user_repository=mock_user_repository,
            authorization_service=mock_authorization_service,
            tracer=mock_tracer
        )

    @pytest.fixture
    def valid_request(self):
        """Valid get user permissions request."""
        return GetUserPermissionsRequestDTO(
            user_id="user-123",
            requesting_user_id="admin-123"
        )

    @pytest.fixture
    def self_request(self):
        """Request for user's own permissions."""
        return GetUserPermissionsRequestDTO(
            user_id="user-123",
            requesting_user_id="user-123"
        )

    @pytest.fixture
    def mock_user(self):
        """Mock user entity."""
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

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_get_user_permissions_success(
        self,
        use_case,
        valid_request,
        mock_user,
        mock_admin_user,
        mock_user_repository,
        mock_authorization_service
    ):
        """Test successful user permissions retrieval."""
        # Arrange
        mock_user_repository.get_by_id.side_effect = lambda user_id: {
            "user-123": mock_user,
            "admin-123": mock_admin_user
        }.get(user_id)

        mock_authorization_service.check_permission.return_value = None
        mock_authorization_service.get_user_permissions.return_value = [
            "read_knowledge_graphs",
            "create_knowledge_graphs",
            "update_knowledge_graphs"
        ]

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is True
        assert response.permissions is not None
        assert response.permissions.user_id == "user-123"
        assert response.permissions.organization_id == "org-123"
        assert response.permissions.role == "editor"
        assert len(response.permissions.permissions) == 3

        # Verify method calls
        assert mock_user_repository.get_by_id.call_count == 2
        mock_authorization_service.check_permission.assert_called_once_with(
            user_id="admin-123",
            resource_id="org-123",
            action="view_user_permissions"
        )
        mock_authorization_service.get_user_permissions.assert_called_once_with(
            user_id="user-123",
            resource_id=None
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_get_own_permissions_success(
        self,
        use_case,
        self_request,
        mock_user,
        mock_user_repository,
        mock_authorization_service
    ):
        """Test successful retrieval of own permissions."""
        # Arrange
        mock_user_repository.get_by_id.return_value = mock_user
        mock_authorization_service.get_user_permissions.return_value = [
            "read_knowledge_graphs",
            "create_knowledge_graphs"
        ]

        # Act
        response = await use_case.execute(self_request)

        # Assert
        assert response.success is True
        assert response.permissions is not None
        assert response.permissions.user_id == "user-123"

        # Verify no authorization check for self-permissions
        mock_authorization_service.check_permission.assert_not_called()
        mock_authorization_service.get_user_permissions.assert_called_once_with(
            user_id="user-123",
            resource_id=None
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_get_permissions_with_resource_id(
        self,
        use_case,
        mock_user,
        mock_user_repository,
        mock_authorization_service
    ):
        """Test getting permissions with specific resource ID."""
        # Arrange
        request = GetUserPermissionsRequestDTO(
            user_id="user-123",
            resource_id="kg-456",
            requesting_user_id="user-123"
        )

        mock_user_repository.get_by_id.return_value = mock_user
        mock_authorization_service.get_user_permissions.side_effect = lambda user_id, resource_id: {
            (None,): ["read_knowledge_graphs", "create_knowledge_graphs"],
            ("kg-456",): ["read_kg", "update_kg"]
        }.get((resource_id,), [])

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.permissions is not None
        assert len(response.permissions.permissions) == 2
        assert "kg-456" in response.permissions.resource_permissions
        assert len(response.permissions.resource_permissions["kg-456"]) == 2

        # Verify both general and resource-specific permissions were requested
        assert mock_authorization_service.get_user_permissions.call_count == 2

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_get_permissions_empty_user_id(self, use_case):
        """Test getting permissions with empty user ID."""
        # Arrange
        request = GetUserPermissionsRequestDTO(
            user_id="",
            requesting_user_id="admin-123"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "User ID is required and cannot be empty" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_get_permissions_empty_requesting_user_id(self, use_case):
        """Test getting permissions with empty requesting user ID."""
        # Arrange
        request = GetUserPermissionsRequestDTO(
            user_id="user-123",
            requesting_user_id=""
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Requesting user ID is required and cannot be empty" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_get_permissions_user_not_found(
        self,
        use_case,
        valid_request,
        mock_user_repository
    ):
        """Test getting permissions when user doesn't exist."""
        # Arrange
        mock_user_repository.get_by_id.return_value = None

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "User with ID 'user-123' not found" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_get_permissions_requesting_user_not_found(
        self,
        use_case,
        valid_request,
        mock_user,
        mock_user_repository
    ):
        """Test getting permissions when requesting user doesn't exist."""
        # Arrange
        mock_user_repository.get_by_id.side_effect = lambda user_id: {
            "user-123": mock_user,
            "admin-123": None
        }.get(user_id)

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "Requesting user with ID 'admin-123' not found" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_get_permissions_different_organization(
        self,
        use_case,
        valid_request,
        mock_user,
        mock_user_repository
    ):
        """Test getting permissions for user in different organization."""
        # Arrange
        different_org_admin = User(
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

        mock_user_repository.get_by_id.side_effect = lambda user_id: {
            "user-123": mock_user,
            "admin-123": different_org_admin
        }.get(user_id)

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "Cannot view permissions of users in different organizations" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_get_permissions_authorization_error(
        self,
        use_case,
        valid_request,
        mock_user,
        mock_admin_user,
        mock_user_repository,
        mock_authorization_service
    ):
        """Test getting permissions with authorization error."""
        # Arrange
        mock_user_repository.get_by_id.side_effect = lambda user_id: {
            "user-123": mock_user,
            "admin-123": mock_admin_user
        }.get(user_id)

        mock_authorization_service.check_permission.side_effect = AuthorizationError(
            message="User lacks permission to view user permissions",
            user_id="admin-123",
            resource_id="org-123",
            required_permission="view_user_permissions"
        )

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "User lacks permission to view user permissions" in response.error_message