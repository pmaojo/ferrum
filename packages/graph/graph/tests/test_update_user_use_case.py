"""Tests for UpdateUserUseCase."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from domain.entities import User, UserRole, Organization, SubscriptionTier
from application.exceptions import (
    ValidationError,
    NotFoundError,
    AuthorizationError,
    BusinessRuleViolationError
)
from application.use_cases.user_org.update_user_use_case import UpdateUserUseCase, UpdateUserResponse
from application.use_cases.dto import UpdateUserRequestDTO, UserDTO


class TestUpdateUserUseCase:
    """Test cases for UpdateUserUseCase."""

    @pytest.fixture
    def mock_user_repository(self):
        """Mock user repository."""
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
        mock_authorization_service,
        mock_audit_service,
        mock_tracer
    ):
        """Create use case instance with mocked dependencies."""
        return UpdateUserUseCase(
            user_repository=mock_user_repository,
            authorization_service=mock_authorization_service,
            audit_service=mock_audit_service,
            tracer=mock_tracer
        )

    @pytest.fixture
    def valid_request(self):
        """Valid update user request."""
        return UpdateUserRequestDTO(
            user_id="user-123",
            name="Updated Name",
            role="editor",
            is_active=True,
            updated_by_user_id="admin-123"
        )

    @pytest.fixture
    def mock_user(self):
        """Mock user entity."""
        return User(
            id="user-123",
            email="test@example.com",
            name="Test User",
            password_hash="hashed_password",
            organization_id="org-123",
            role=UserRole.VIEWER,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_login=None,
            is_active=True
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_update_user_success(
        self,
        use_case,
        valid_request,
        mock_user,
        mock_user_repository,
        mock_authorization_service,
        mock_audit_service
    ):
        """Test successful user update."""
        # Arrange
        mock_user_repository.get_by_id.return_value = mock_user
        mock_authorization_service.check_permission.return_value = None
        mock_user_repository.update.return_value = mock_user

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is True
        assert response.user is not None
        assert response.user.name == "Updated Name"
        assert response.user.role == "editor"
        assert response.user.is_active is True

        # Verify method calls
        mock_user_repository.get_by_id.assert_called_once_with("user-123")
        mock_authorization_service.check_permission.assert_called_once_with(
            user_id="admin-123",
            resource_id="org-123",
            action="manage_users"
        )
        mock_user_repository.update.assert_called_once()
        mock_audit_service.log_activity.assert_called_once()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_update_user_self_update_name_only(
        self,
        use_case,
        mock_user,
        mock_user_repository,
        mock_audit_service
    ):
        """Test user updating their own name."""
        # Arrange
        request = UpdateUserRequestDTO(
            user_id="user-123",
            name="Updated Name",
            updated_by_user_id="user-123"  # Same user
        )
        mock_user_repository.get_by_id.return_value = mock_user
        mock_user_repository.update.return_value = mock_user

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.user.name == "Updated Name"

        # Verify no authorization check for self-update
        mock_user_repository.get_by_id.assert_called_once_with("user-123")
        mock_user_repository.update.assert_called_once()
        mock_audit_service.log_activity.assert_called_once()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_update_user_self_update_role_forbidden(
        self,
        use_case,
        mock_user,
        mock_user_repository
    ):
        """Test user cannot update their own role."""
        # Arrange
        request = UpdateUserRequestDTO(
            user_id="user-123",
            role="admin",
            updated_by_user_id="user-123"  # Same user
        )
        mock_user_repository.get_by_id.return_value = mock_user

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Users can only update their own name" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_update_user_no_changes(
        self,
        use_case,
        mock_user,
        mock_user_repository,
        mock_authorization_service
    ):
        """Test update with no actual changes."""
        # Arrange
        request = UpdateUserRequestDTO(
            user_id="user-123",
            name="Test User",  # Same as current name
            role="viewer",     # Same as current role
            updated_by_user_id="admin-123"
        )
        mock_user_repository.get_by_id.return_value = mock_user
        mock_authorization_service.check_permission.return_value = None

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.user is not None

        # Verify update was not called since no changes
        mock_user_repository.update.assert_not_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_update_user_empty_user_id(self, use_case):
        """Test update with empty user ID."""
        # Arrange
        request = UpdateUserRequestDTO(
            user_id="",
            name="Updated Name",
            updated_by_user_id="admin-123"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "User ID is required and cannot be empty" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_update_user_empty_updated_by_user_id(self, use_case):
        """Test update with empty updated_by_user_id."""
        # Arrange
        request = UpdateUserRequestDTO(
            user_id="user-123",
            name="Updated Name",
            updated_by_user_id=""
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Updated by user ID is required and cannot be empty" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_update_user_empty_name(self, use_case):
        """Test update with empty name."""
        # Arrange
        request = UpdateUserRequestDTO(
            user_id="user-123",
            name="",
            updated_by_user_id="admin-123"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Name cannot be empty if provided" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_update_user_long_name(self, use_case):
        """Test update with name that's too long."""
        # Arrange
        long_name = "a" * 256
        request = UpdateUserRequestDTO(
            user_id="user-123",
            name=long_name,
            updated_by_user_id="admin-123"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Name cannot exceed 255 characters" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_update_user_invalid_role(self, use_case):
        """Test update with invalid role."""
        # Arrange
        request = UpdateUserRequestDTO(
            user_id="user-123",
            role="invalid_role",
            updated_by_user_id="admin-123"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Role must be one of:" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_update_user_not_found(
        self,
        use_case,
        valid_request,
        mock_user_repository
    ):
        """Test update when user doesn't exist."""
        # Arrange
        mock_user_repository.get_by_id.return_value = None

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "User with ID 'user-123' not found" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_update_user_authorization_error(
        self,
        use_case,
        valid_request,
        mock_user,
        mock_user_repository,
        mock_authorization_service
    ):
        """Test update with authorization error."""
        # Arrange
        mock_user_repository.get_by_id.return_value = mock_user
        mock_authorization_service.check_permission.side_effect = AuthorizationError(
            message="User lacks permission to manage users",
            user_id="admin-123",
            resource_id="org-123",
            required_permission="manage_users"
        )

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "User lacks permission to manage users" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_update_inactive_user(
        self,
        use_case,
        valid_request,
        mock_user,
        mock_user_repository,
        mock_authorization_service
    ):
        """Test update of inactive user."""
        # Arrange
        mock_user.is_active = False
        mock_user_repository.get_by_id.return_value = mock_user
        mock_authorization_service.check_permission.return_value = None

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "Cannot update inactive user" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_update_user_deactivate(
        self,
        use_case,
        mock_user,
        mock_user_repository,
        mock_authorization_service,
        mock_audit_service
    ):
        """Test deactivating a user."""
        # Arrange
        request = UpdateUserRequestDTO(
            user_id="user-123",
            is_active=False,
            updated_by_user_id="admin-123"
        )
        mock_user_repository.get_by_id.return_value = mock_user
        mock_authorization_service.check_permission.return_value = None
        mock_user_repository.update.return_value = mock_user

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.user.is_active is False

        # Verify deactivate was called
        assert mock_user.is_active is False
        mock_user_repository.update.assert_called_once()
        mock_audit_service.log_activity.assert_called_once()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_update_user_role_change(
        self,
        use_case,
        mock_user,
        mock_user_repository,
        mock_authorization_service,
        mock_audit_service
    ):
        """Test changing user role."""
        # Arrange
        request = UpdateUserRequestDTO(
            user_id="user-123",
            role="admin",
            updated_by_user_id="admin-123"
        )
        mock_user_repository.get_by_id.return_value = mock_user
        mock_authorization_service.check_permission.return_value = None
        mock_user_repository.update.return_value = mock_user

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.user.role == "admin"

        # Verify role was updated
        assert mock_user.role == UserRole.ADMIN
        mock_user_repository.update.assert_called_once()
        mock_audit_service.log_activity.assert_called_once()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_update_user_multiple_fields(
        self,
        use_case,
        mock_user,
        mock_user_repository,
        mock_authorization_service,
        mock_audit_service
    ):
        """Test updating multiple fields at once."""
        # Arrange
        request = UpdateUserRequestDTO(
            user_id="user-123",
            name="New Name",
            role="editor",
            is_active=True,
            updated_by_user_id="admin-123"
        )
        mock_user_repository.get_by_id.return_value = mock_user
        mock_authorization_service.check_permission.return_value = None
        mock_user_repository.update.return_value = mock_user

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.user.name == "New Name"
        assert response.user.role == "editor"
        assert response.user.is_active is True

        # Verify all fields were updated
        assert mock_user.name == "New Name"
        assert mock_user.role == UserRole.EDITOR
        assert mock_user.is_active is True
        mock_user_repository.update.assert_called_once()
        mock_audit_service.log_activity.assert_called_once()