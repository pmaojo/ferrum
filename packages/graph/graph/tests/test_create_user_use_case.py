"""Tests for CreateUserUseCase."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from domain.entities import User, UserRole, Organization, SubscriptionTier
from application.exceptions import (
    ValidationError,
    NotFoundError,
    AuthorizationError,
    BusinessRuleViolationError
)
from application.use_cases.user_org.create_user_use_case import CreateUserUseCase, CreateUserResponse
from application.use_cases.dto import CreateUserRequestDTO, UserDTO


class TestCreateUserUseCase:
    """Test cases for CreateUserUseCase."""

    @pytest.fixture
    def mock_user_repository(self):
        """Mock user repository."""
        return Mock()

    @pytest.fixture
    def mock_organization_repository(self):
        """Mock organization repository."""
        return Mock()

    @pytest.fixture
    def mock_password_service(self):
        """Mock password service."""
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
        mock_password_service,
        mock_authorization_service,
        mock_audit_service,
        mock_tracer
    ):
        """Create use case instance with mocked dependencies."""
        return CreateUserUseCase(
            user_repository=mock_user_repository,
            organization_repository=mock_organization_repository,
            password_service=mock_password_service,
            authorization_service=mock_authorization_service,
            audit_service=mock_audit_service,
            tracer=mock_tracer
        )

    @pytest.fixture
    def valid_request(self):
        """Valid create user request."""
        return CreateUserRequestDTO(
            email="test@example.com",
            name="Test User",
            password="SecurePass123",
            organization_id="org-123",
            role="viewer",
            created_by_user_id="creator-123"
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
    async def test_create_user_success(
        self,
        use_case,
        valid_request,
        mock_organization,
        mock_user,
        mock_user_repository,
        mock_organization_repository,
        mock_password_service,
        mock_authorization_service,
        mock_audit_service
    ):
        """Test successful user creation."""
        # Arrange
        mock_authorization_service.check_permission.return_value = None
        mock_organization_repository.get_by_id.return_value = mock_organization
        mock_user_repository.get_by_email.return_value = None
        mock_password_service.hash_password.return_value = "hashed_password"
        mock_user_repository.create.return_value = mock_user

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is True
        assert response.user is not None
        assert response.user.email == "test@example.com"
        assert response.user.name == "Test User"
        assert response.user.role == "viewer"
        assert response.user.organization_id == "org-123"

        # Verify method calls
        mock_authorization_service.check_permission.assert_called_once_with(
            user_id="creator-123",
            resource_id="org-123",
            action="manage_users"
        )
        mock_organization_repository.get_by_id.assert_called_once_with("org-123")
        mock_user_repository.get_by_email.assert_called_once_with("test@example.com")
        mock_password_service.hash_password.assert_called_once_with("SecurePass123")
        mock_user_repository.create.assert_called_once()
        mock_audit_service.log_activity.assert_called_once()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_user_invalid_email(self, use_case):
        """Test user creation with invalid email."""
        # Arrange
        request = CreateUserRequestDTO(
            email="invalid-email",
            name="Test User",
            password="SecurePass123",
            organization_id="org-123",
            role="viewer",
            created_by_user_id="creator-123"
        )

        # Act & Assert
        response = await use_case.execute(request)
        assert response.success is False
        assert "Email must be in valid format" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_user_empty_email(self, use_case):
        """Test user creation with empty email."""
        # Arrange
        request = CreateUserRequestDTO(
            email="",
            name="Test User",
            password="SecurePass123",
            organization_id="org-123",
            role="viewer",
            created_by_user_id="creator-123"
        )

        # Act & Assert
        response = await use_case.execute(request)
        assert response.success is False
        assert "Email is required and cannot be empty" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_user_empty_name(self, use_case):
        """Test user creation with empty name."""
        # Arrange
        request = CreateUserRequestDTO(
            email="test@example.com",
            name="",
            password="SecurePass123",
            organization_id="org-123",
            role="viewer",
            created_by_user_id="creator-123"
        )

        # Act & Assert
        response = await use_case.execute(request)
        assert response.success is False
        assert "Name is required and cannot be empty" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_user_weak_password(self, use_case):
        """Test user creation with weak password."""
        # Arrange
        request = CreateUserRequestDTO(
            email="test@example.com",
            name="Test User",
            password="weak",
            organization_id="org-123",
            role="viewer",
            created_by_user_id="creator-123"
        )

        # Act & Assert
        response = await use_case.execute(request)
        assert response.success is False
        assert "Password must be at least 8 characters long" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_user_password_no_uppercase(self, use_case):
        """Test user creation with password missing uppercase letter."""
        # Arrange
        request = CreateUserRequestDTO(
            email="test@example.com",
            name="Test User",
            password="securepass123",
            organization_id="org-123",
            role="viewer",
            created_by_user_id="creator-123"
        )

        # Act & Assert
        response = await use_case.execute(request)
        assert response.success is False
        assert "Password must contain at least one uppercase letter" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_user_password_no_lowercase(self, use_case):
        """Test user creation with password missing lowercase letter."""
        # Arrange
        request = CreateUserRequestDTO(
            email="test@example.com",
            name="Test User",
            password="SECUREPASS123",
            organization_id="org-123",
            role="viewer",
            created_by_user_id="creator-123"
        )

        # Act & Assert
        response = await use_case.execute(request)
        assert response.success is False
        assert "Password must contain at least one lowercase letter" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_user_password_no_digit(self, use_case):
        """Test user creation with password missing digit."""
        # Arrange
        request = CreateUserRequestDTO(
            email="test@example.com",
            name="Test User",
            password="SecurePassword",
            organization_id="org-123",
            role="viewer",
            created_by_user_id="creator-123"
        )

        # Act & Assert
        response = await use_case.execute(request)
        assert response.success is False
        assert "Password must contain at least one digit" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_user_invalid_role(self, use_case):
        """Test user creation with invalid role."""
        # Arrange
        request = CreateUserRequestDTO(
            email="test@example.com",
            name="Test User",
            password="SecurePass123",
            organization_id="org-123",
            role="invalid_role",
            created_by_user_id="creator-123"
        )

        # Act & Assert
        response = await use_case.execute(request)
        assert response.success is False
        assert "Role must be one of:" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_user_authorization_error(
        self,
        use_case,
        valid_request,
        mock_authorization_service
    ):
        """Test user creation with authorization error."""
        # Arrange
        mock_authorization_service.check_permission.side_effect = AuthorizationError(
            message="User lacks permission to manage users",
            user_id="creator-123",
            resource_id="org-123",
            required_permission="manage_users"
        )

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "User lacks permission to manage users" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_user_organization_not_found(
        self,
        use_case,
        valid_request,
        mock_authorization_service,
        mock_organization_repository
    ):
        """Test user creation when organization doesn't exist."""
        # Arrange
        mock_authorization_service.check_permission.return_value = None
        mock_organization_repository.get_by_id.return_value = None

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "Organization with ID 'org-123' not found" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_user_inactive_organization(
        self,
        use_case,
        valid_request,
        mock_organization,
        mock_authorization_service,
        mock_organization_repository
    ):
        """Test user creation in inactive organization."""
        # Arrange
        mock_organization.is_active = False
        mock_authorization_service.check_permission.return_value = None
        mock_organization_repository.get_by_id.return_value = mock_organization

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "Cannot create users in inactive organization" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_user_duplicate_email(
        self,
        use_case,
        valid_request,
        mock_organization,
        mock_user,
        mock_authorization_service,
        mock_organization_repository,
        mock_user_repository
    ):
        """Test user creation with duplicate email."""
        # Arrange
        mock_authorization_service.check_permission.return_value = None
        mock_organization_repository.get_by_id.return_value = mock_organization
        mock_user_repository.get_by_email.return_value = mock_user

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "User with email 'test@example.com' already exists" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_user_long_email(self, use_case):
        """Test user creation with email that's too long."""
        # Arrange
        long_email = "a" * 250 + "@example.com"
        request = CreateUserRequestDTO(
            email=long_email,
            name="Test User",
            password="SecurePass123",
            organization_id="org-123",
            role="viewer",
            created_by_user_id="creator-123"
        )

        # Act & Assert
        response = await use_case.execute(request)
        assert response.success is False
        assert "Email cannot exceed 255 characters" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_user_long_name(self, use_case):
        """Test user creation with name that's too long."""
        # Arrange
        long_name = "a" * 256
        request = CreateUserRequestDTO(
            email="test@example.com",
            name=long_name,
            password="SecurePass123",
            organization_id="org-123",
            role="viewer",
            created_by_user_id="creator-123"
        )

        # Act & Assert
        response = await use_case.execute(request)
        assert response.success is False
        assert "Name cannot exceed 255 characters" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_user_long_password(self, use_case):
        """Test user creation with password that's too long."""
        # Arrange
        long_password = "SecurePass123" + "a" * 120
        request = CreateUserRequestDTO(
            email="test@example.com",
            name="Test User",
            password=long_password,
            organization_id="org-123",
            role="viewer",
            created_by_user_id="creator-123"
        )

        # Act & Assert
        response = await use_case.execute(request)
        assert response.success is False
        assert "Password cannot exceed 128 characters" in response.error_message