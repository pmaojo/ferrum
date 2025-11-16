"""Tests for CreateOrganizationUseCase."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from domain.entities import Organization, SubscriptionTier, User, UserRole
from application.exceptions import (
    ValidationError,
    BusinessRuleViolationError
)
from application.use_cases.user_org.create_organization_use_case import CreateOrganizationUseCase, CreateOrganizationResponse
from application.use_cases.dto import CreateOrganizationRequestDTO, OrganizationDTO, UserDTO


class TestCreateOrganizationUseCase:
    """Test cases for CreateOrganizationUseCase."""

    @pytest.fixture
    def mock_organization_repository(self):
        """Mock organization repository."""
        return Mock()

    @pytest.fixture
    def mock_user_repository(self):
        """Mock user repository."""
        return Mock()

    @pytest.fixture
    def mock_password_service(self):
        """Mock password service."""
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
        mock_organization_repository,
        mock_user_repository,
        mock_password_service,
        mock_audit_service,
        mock_tracer
    ):
        """Create use case instance with mocked dependencies."""
        return CreateOrganizationUseCase(
            organization_repository=mock_organization_repository,
            user_repository=mock_user_repository,
            password_service=mock_password_service,
            audit_service=mock_audit_service,
            tracer=mock_tracer
        )

    @pytest.fixture
    def valid_request_without_admin(self):
        """Valid create organization request without admin user."""
        return CreateOrganizationRequestDTO(
            name="Test Organization",
            subscription_tier="free"
        )

    @pytest.fixture
    def valid_request_with_admin(self):
        """Valid create organization request with admin user."""
        return CreateOrganizationRequestDTO(
            name="Test Organization",
            subscription_tier="basic",
            admin_email="admin@example.com",
            admin_name="Admin User",
            admin_password="AdminPass123"
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
            id="user-123",
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
    async def test_create_organization_without_admin_success(
        self,
        use_case,
        valid_request_without_admin,
        mock_organization,
        mock_organization_repository,
        mock_audit_service
    ):
        """Test successful organization creation without admin user."""
        # Arrange
        mock_organization_repository.get_by_name.return_value = None
        mock_organization_repository.create.return_value = mock_organization

        # Act
        response = await use_case.execute(valid_request_without_admin)

        # Assert
        assert response.success is True
        assert response.organization is not None
        assert response.organization.name == "Test Organization"
        assert response.organization.subscription_tier == "free"
        assert response.admin_user is None

        # Verify method calls
        mock_organization_repository.get_by_name.assert_called_once_with("Test Organization")
        mock_organization_repository.create.assert_called_once()
        mock_audit_service.log_activity.assert_called_once()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_organization_with_admin_success(
        self,
        use_case,
        valid_request_with_admin,
        mock_organization,
        mock_admin_user,
        mock_organization_repository,
        mock_user_repository,
        mock_password_service,
        mock_audit_service
    ):
        """Test successful organization creation with admin user."""
        # Arrange
        mock_organization_repository.get_by_name.return_value = None
        mock_organization_repository.create.return_value = mock_organization
        mock_user_repository.get_by_email.return_value = None
        mock_password_service.hash_password.return_value = "hashed_password"
        mock_user_repository.create.return_value = mock_admin_user

        # Act
        response = await use_case.execute(valid_request_with_admin)

        # Assert
        assert response.success is True
        assert response.organization is not None
        assert response.organization.name == "Test Organization"
        assert response.admin_user is not None
        assert response.admin_user.email == "admin@example.com"
        assert response.admin_user.role == "admin"

        # Verify method calls
        mock_organization_repository.get_by_name.assert_called_once_with("Test Organization")
        mock_organization_repository.create.assert_called_once()
        mock_user_repository.get_by_email.assert_called_once_with("admin@example.com")
        mock_password_service.hash_password.assert_called_once_with("AdminPass123")
        mock_user_repository.create.assert_called_once()
        assert mock_audit_service.log_activity.call_count == 2  # Organization and admin user

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_organization_empty_name(self, use_case):
        """Test organization creation with empty name."""
        # Arrange
        request = CreateOrganizationRequestDTO(
            name="",
            subscription_tier="free"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Organization name is required and cannot be empty" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_organization_long_name(self, use_case):
        """Test organization creation with name that's too long."""
        # Arrange
        long_name = "a" * 256
        request = CreateOrganizationRequestDTO(
            name=long_name,
            subscription_tier="free"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Organization name cannot exceed 255 characters" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_organization_invalid_subscription_tier(self, use_case):
        """Test organization creation with invalid subscription tier."""
        # Arrange
        request = CreateOrganizationRequestDTO(
            name="Test Organization",
            subscription_tier="invalid_tier"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Subscription tier must be one of:" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_organization_invalid_admin_email(self, use_case):
        """Test organization creation with invalid admin email."""
        # Arrange
        request = CreateOrganizationRequestDTO(
            name="Test Organization",
            subscription_tier="basic",
            admin_email="invalid-email",
            admin_name="Admin User",
            admin_password="AdminPass123"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Admin email must be in valid format" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_organization_weak_admin_password(self, use_case):
        """Test organization creation with weak admin password."""
        # Arrange
        request = CreateOrganizationRequestDTO(
            name="Test Organization",
            subscription_tier="basic",
            admin_email="admin@example.com",
            admin_name="Admin User",
            admin_password="weak"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Admin password must be at least 8 characters long" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_organization_admin_password_no_uppercase(self, use_case):
        """Test organization creation with admin password missing uppercase letter."""
        # Arrange
        request = CreateOrganizationRequestDTO(
            name="Test Organization",
            subscription_tier="basic",
            admin_email="admin@example.com",
            admin_name="Admin User",
            admin_password="adminpass123"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Admin password must contain at least one uppercase letter" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_organization_partial_admin_details(self, use_case):
        """Test organization creation with partial admin details."""
        # Arrange
        request = CreateOrganizationRequestDTO(
            name="Test Organization",
            subscription_tier="basic",
            admin_email="admin@example.com",
            admin_name="Admin User"
            # Missing admin_password
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "admin_email, admin_name, and admin_password are all required" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_organization_duplicate_name(
        self,
        use_case,
        valid_request_without_admin,
        mock_organization,
        mock_organization_repository
    ):
        """Test organization creation with duplicate name."""
        # Arrange
        mock_organization_repository.get_by_name.return_value = mock_organization

        # Act
        response = await use_case.execute(valid_request_without_admin)

        # Assert
        assert response.success is False
        assert "Organization with name 'Test Organization' already exists" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_organization_duplicate_admin_email(
        self,
        use_case,
        valid_request_with_admin,
        mock_admin_user,
        mock_organization_repository,
        mock_user_repository
    ):
        """Test organization creation with duplicate admin email."""
        # Arrange
        mock_organization_repository.get_by_name.return_value = None
        mock_user_repository.get_by_email.return_value = mock_admin_user

        # Act
        response = await use_case.execute(valid_request_with_admin)

        # Assert
        assert response.success is False
        assert "User with email 'admin@example.com' already exists" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_organization_long_admin_email(self, use_case):
        """Test organization creation with admin email that's too long."""
        # Arrange
        long_email = "a" * 250 + "@example.com"
        request = CreateOrganizationRequestDTO(
            name="Test Organization",
            subscription_tier="basic",
            admin_email=long_email,
            admin_name="Admin User",
            admin_password="AdminPass123"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Admin email cannot exceed 255 characters" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_organization_long_admin_name(self, use_case):
        """Test organization creation with admin name that's too long."""
        # Arrange
        long_name = "a" * 256
        request = CreateOrganizationRequestDTO(
            name="Test Organization",
            subscription_tier="basic",
            admin_email="admin@example.com",
            admin_name=long_name,
            admin_password="AdminPass123"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Admin name cannot exceed 255 characters" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_organization_long_admin_password(self, use_case):
        """Test organization creation with admin password that's too long."""
        # Arrange
        long_password = "AdminPass123" + "a" * 120
        request = CreateOrganizationRequestDTO(
            name="Test Organization",
            subscription_tier="basic",
            admin_email="admin@example.com",
            admin_name="Admin User",
            admin_password=long_password
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Admin password cannot exceed 128 characters" in response.error_message