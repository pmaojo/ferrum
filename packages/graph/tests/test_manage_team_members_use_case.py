"""Tests for ManageTeamMembersUseCase."""

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
from application.use_cases.user_org.manage_team_members_use_case import ManageTeamMembersUseCase, ManageTeamMembersResponse
from application.use_cases.dto import ManageTeamMembersRequestDTO, UserDTO


class TestManageTeamMembersUseCase:
    """Test cases for ManageTeamMembersUseCase."""

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
        return ManageTeamMembersUseCase(
            user_repository=mock_user_repository,
            organization_repository=mock_organization_repository,
            authorization_service=mock_authorization_service,
            audit_service=mock_audit_service,
            tracer=mock_tracer
        )

    @pytest.fixture
    def valid_add_request(self):
        """Valid add team members request."""
        return ManageTeamMembersRequestDTO(
            organization_id="org-123",
            action="add",
            user_ids=["user-1", "user-2"],
            manager_user_id="manager-123"
        )

    @pytest.fixture
    def valid_remove_request(self):
        """Valid remove team members request."""
        return ManageTeamMembersRequestDTO(
            organization_id="org-123",
            action="remove",
            user_ids=["user-1", "user-2"],
            manager_user_id="manager-123"
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
    def mock_users(self):
        """Mock user entities."""
        return [
            User(
                id="user-1",
                email="user1@example.com",
                name="User One",
                password_hash="hashed_password",
                organization_id="other-org",  # Different org initially
                role=UserRole.VIEWER,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_login=None,
                is_active=True
            ),
            User(
                id="user-2",
                email="user2@example.com",
                name="User Two",
                password_hash="hashed_password",
                organization_id="other-org",  # Different org initially
                role=UserRole.EDITOR,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_login=None,
                is_active=True
            )
        ]

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_add_team_members_success(
        self,
        use_case,
        valid_add_request,
        mock_organization,
        mock_users,
        mock_user_repository,
        mock_organization_repository,
        mock_authorization_service,
        mock_audit_service
    ):
        """Test successful addition of team members."""
        # Arrange
        mock_authorization_service.check_permission.return_value = None
        mock_organization_repository.get_by_id.return_value = mock_organization
        mock_user_repository.get_by_id.side_effect = lambda user_id: next(
            (user for user in mock_users if user.id == user_id), None
        )
        mock_user_repository.update.side_effect = lambda user: user

        # Act
        response = await use_case.execute(valid_add_request)

        # Assert
        assert response.success is True
        assert len(response.affected_users) == 2
        assert response.action_performed == "add"

        # Verify users were updated to new organization
        for user in mock_users:
            assert user.organization_id == "org-123"

        # Verify method calls
        mock_authorization_service.check_permission.assert_called_once_with(
            user_id="manager-123",
            resource_id="org-123",
            action="manage_users"
        )
        mock_organization_repository.get_by_id.assert_called_once_with("org-123")
        assert mock_user_repository.update.call_count == 2
        assert mock_audit_service.log_activity.call_count == 2

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_remove_team_members_success(
        self,
        use_case,
        valid_remove_request,
        mock_organization,
        mock_users,
        mock_user_repository,
        mock_organization_repository,
        mock_authorization_service,
        mock_audit_service
    ):
        """Test successful removal of team members."""
        # Arrange - set users to be in the target organization
        for user in mock_users:
            user.organization_id = "org-123"

        mock_authorization_service.check_permission.return_value = None
        mock_organization_repository.get_by_id.return_value = mock_organization
        mock_user_repository.get_by_id.side_effect = lambda user_id: next(
            (user for user in mock_users if user.id == user_id), None
        )
        mock_user_repository.update.side_effect = lambda user: user

        # Act
        response = await use_case.execute(valid_remove_request)

        # Assert
        assert response.success is True
        assert len(response.affected_users) == 2
        assert response.action_performed == "remove"

        # Verify users were deactivated
        for user in mock_users:
            assert user.is_active is False

        # Verify method calls
        assert mock_user_repository.update.call_count == 2
        assert mock_audit_service.log_activity.call_count == 2

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_add_team_members_already_in_organization(
        self,
        use_case,
        valid_add_request,
        mock_organization,
        mock_users,
        mock_user_repository,
        mock_organization_repository,
        mock_authorization_service
    ):
        """Test adding users who are already in the organization."""
        # Arrange - set users to already be in the target organization
        for user in mock_users:
            user.organization_id = "org-123"

        mock_authorization_service.check_permission.return_value = None
        mock_organization_repository.get_by_id.return_value = mock_organization
        mock_user_repository.get_by_id.side_effect = lambda user_id: next(
            (user for user in mock_users if user.id == user_id), None
        )

        # Act
        response = await use_case.execute(valid_add_request)

        # Assert
        assert response.success is True
        assert len(response.affected_users) == 0  # No users were actually added

        # Verify no updates were made
        mock_user_repository.update.assert_not_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_remove_team_members_not_in_organization(
        self,
        use_case,
        valid_remove_request,
        mock_organization,
        mock_users,
        mock_user_repository,
        mock_organization_repository,
        mock_authorization_service
    ):
        """Test removing users who are not in the organization."""
        # Arrange - users are in different organization
        mock_authorization_service.check_permission.return_value = None
        mock_organization_repository.get_by_id.return_value = mock_organization
        mock_user_repository.get_by_id.side_effect = lambda user_id: next(
            (user for user in mock_users if user.id == user_id), None
        )

        # Act
        response = await use_case.execute(valid_remove_request)

        # Assert
        assert response.success is True
        assert len(response.affected_users) == 0  # No users were actually removed

        # Verify no updates were made
        mock_user_repository.update.assert_not_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_manage_team_members_empty_organization_id(self, use_case):
        """Test team management with empty organization ID."""
        # Arrange
        request = ManageTeamMembersRequestDTO(
            organization_id="",
            action="add",
            user_ids=["user-1"],
            manager_user_id="manager-123"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Organization ID is required and cannot be empty" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_manage_team_members_invalid_action(self, use_case):
        """Test team management with invalid action."""
        # Arrange
        request = ManageTeamMembersRequestDTO(
            organization_id="org-123",
            action="invalid_action",
            user_ids=["user-1"],
            manager_user_id="manager-123"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Action must be one of: add, remove" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_manage_team_members_empty_user_ids(self, use_case):
        """Test team management with empty user IDs list."""
        # Arrange
        request = ManageTeamMembersRequestDTO(
            organization_id="org-123",
            action="add",
            user_ids=[],
            manager_user_id="manager-123"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "At least one user ID must be provided" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_manage_team_members_duplicate_user_ids(self, use_case):
        """Test team management with duplicate user IDs."""
        # Arrange
        request = ManageTeamMembersRequestDTO(
            organization_id="org-123",
            action="add",
            user_ids=["user-1", "user-1"],
            manager_user_id="manager-123"
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Duplicate user IDs are not allowed" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_manage_team_members_authorization_error(
        self,
        use_case,
        valid_add_request,
        mock_authorization_service
    ):
        """Test team management with authorization error."""
        # Arrange
        mock_authorization_service.check_permission.side_effect = AuthorizationError(
            message="User lacks permission to manage users",
            user_id="manager-123",
            resource_id="org-123",
            required_permission="manage_users"
        )

        # Act
        response = await use_case.execute(valid_add_request)

        # Assert
        assert response.success is False
        assert "User lacks permission to manage users" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_manage_team_members_organization_not_found(
        self,
        use_case,
        valid_add_request,
        mock_authorization_service,
        mock_organization_repository
    ):
        """Test team management when organization doesn't exist."""
        # Arrange
        mock_authorization_service.check_permission.return_value = None
        mock_organization_repository.get_by_id.return_value = None

        # Act
        response = await use_case.execute(valid_add_request)

        # Assert
        assert response.success is False
        assert "Organization with ID 'org-123' not found" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_manage_team_members_inactive_organization(
        self,
        use_case,
        valid_add_request,
        mock_organization,
        mock_authorization_service,
        mock_organization_repository
    ):
        """Test team management in inactive organization."""
        # Arrange
        mock_organization.is_active = False
        mock_authorization_service.check_permission.return_value = None
        mock_organization_repository.get_by_id.return_value = mock_organization

        # Act
        response = await use_case.execute(valid_add_request)

        # Assert
        assert response.success is False
        assert "Cannot manage team members in inactive organization" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_manage_team_members_user_not_found(
        self,
        use_case,
        valid_add_request,
        mock_organization,
        mock_authorization_service,
        mock_organization_repository,
        mock_user_repository
    ):
        """Test team management when user doesn't exist."""
        # Arrange
        mock_authorization_service.check_permission.return_value = None
        mock_organization_repository.get_by_id.return_value = mock_organization
        mock_user_repository.get_by_id.return_value = None

        # Act
        response = await use_case.execute(valid_add_request)

        # Assert
        assert response.success is False
        assert "Users not found:" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_add_inactive_user(
        self,
        use_case,
        valid_add_request,
        mock_organization,
        mock_users,
        mock_user_repository,
        mock_organization_repository,
        mock_authorization_service
    ):
        """Test adding inactive user to organization."""
        # Arrange
        mock_users[0].is_active = False
        mock_authorization_service.check_permission.return_value = None
        mock_organization_repository.get_by_id.return_value = mock_organization
        mock_user_repository.get_by_id.side_effect = lambda user_id: next(
            (user for user in mock_users if user.id == user_id), None
        )

        # Act
        response = await use_case.execute(valid_add_request)

        # Assert
        assert response.success is False
        assert "Cannot add inactive user" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_remove_self_from_organization(
        self,
        use_case,
        mock_organization,
        mock_users,
        mock_user_repository,
        mock_organization_repository,
        mock_authorization_service
    ):
        """Test user trying to remove themselves from organization."""
        # Arrange
        request = ManageTeamMembersRequestDTO(
            organization_id="org-123",
            action="remove",
            user_ids=["manager-123"],  # Manager trying to remove themselves
            manager_user_id="manager-123"
        )

        # Set up manager user
        manager_user = User(
            id="manager-123",
            email="manager@example.com",
            name="Manager User",
            password_hash="hashed_password",
            organization_id="org-123",
            role=UserRole.ADMIN,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_login=None,
            is_active=True
        )

        mock_authorization_service.check_permission.return_value = None
        mock_organization_repository.get_by_id.return_value = mock_organization
        mock_user_repository.get_by_id.return_value = manager_user

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Users cannot remove themselves from the organization" in response.error_message