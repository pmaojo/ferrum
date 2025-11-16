"""Tests for ManageAPIKeysUseCase."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from application.ports.security import APIKeyManagementPort, AuthorizationPort
from application.use_cases.dto import ManageAPIKeysRequestDTO
from application.use_cases.webhook.manage_api_keys_use_case import ManageAPIKeysUseCase
from domain.exceptions import ValidationError, AuthorizationError, NotFoundError


class TestManageAPIKeysUseCase:
    """Test cases for ManageAPIKeysUseCase."""

    def setup_method(self):
        """Set up test dependencies."""
        self.api_key_management_service = Mock(spec=APIKeyManagementPort)
        self.authorization_service = Mock(spec=AuthorizationPort)
        self.use_case = ManageAPIKeysUseCase(
            api_key_management_service=self.api_key_management_service,
            authorization_service=self.authorization_service,
        )

    def test_create_api_key_success(self):
        """Test successful API key creation."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="create",
            name="Test API Key",
            scopes=["knowledge_graph:read", "ontology:read"],
            expires_at=datetime.now() + timedelta(days=30),
            rate_limit=1000,
        )

        created_key_data = {
            "id": "key-789",
            "name": "Test API Key",
            "tenant_id": "tenant-123",
            "scopes": ["knowledge_graph:read", "ontology:read"],
            "key_prefix": "ak_12345",
            "expires_at": request.expires_at,
            "rate_limit": 1000,
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "last_used_at": None,
            "usage_count": 0,
        }

        self.api_key_management_service.create_api_key.return_value = created_key_data

        # Act
        with patch('secrets.token_hex', return_value='1234567890abcdef' * 4):
            result = self.use_case.execute(request)

        # Assert
        assert result.action == "create"
        assert result.success is True
        assert result.api_key is not None
        assert result.api_key.id == "key-789"
        assert result.api_key.name == "Test API Key"
        assert result.api_key.scopes == ["knowledge_graph:read", "ontology:read"]
        assert result.api_key.rate_limit == 1000
        assert result.full_key == "ak_1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        assert result.message == "API key created successfully"

        # Verify authorization check
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-456",
            resource_type="api_key",
            action="create",
            tenant_id="tenant-123",
        )

        # Verify service call
        self.api_key_management_service.create_api_key.assert_called_once()
        call_args = self.api_key_management_service.create_api_key.call_args
        assert call_args[1]["tenant_id"] == "tenant-123"
        assert call_args[1]["api_key_data"]["name"] == "Test API Key"
        assert call_args[1]["api_key_data"]["scopes"] == ["knowledge_graph:read", "ontology:read"]

    def test_update_api_key_success(self):
        """Test successful API key update."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="update",
            api_key_id="key-789",
            name="Updated API Key",
            scopes=["knowledge_graph:write"],
            rate_limit=2000,
        )

        existing_key_data = {
            "id": "key-789",
            "name": "Test API Key",
            "tenant_id": "tenant-123",
            "scopes": ["knowledge_graph:read"],
            "key_prefix": "ak_12345",
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "usage_count": 5,
        }

        updated_key_data = {
            **existing_key_data,
            "name": "Updated API Key",
            "scopes": ["knowledge_graph:write"],
            "rate_limit": 2000,
            "updated_at": datetime.now(),
        }

        self.api_key_management_service.get_api_key.return_value = existing_key_data
        self.api_key_management_service.update_api_key.return_value = updated_key_data

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.action == "update"
        assert result.success is True
        assert result.api_key.name == "Updated API Key"
        assert result.api_key.scopes == ["knowledge_graph:write"]
        assert result.api_key.rate_limit == 2000
        assert result.message == "API key updated successfully"

        # Verify service calls
        self.api_key_management_service.get_api_key.assert_called_once_with(
            tenant_id="tenant-123",
            api_key_id="key-789",
        )
        self.api_key_management_service.update_api_key.assert_called_once()

    def test_delete_api_key_success(self):
        """Test successful API key deletion."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="delete",
            api_key_id="key-789",
        )

        existing_key_data = {
            "id": "key-789",
            "name": "Test API Key",
            "tenant_id": "tenant-123",
        }

        self.api_key_management_service.get_api_key.return_value = existing_key_data
        self.api_key_management_service.delete_api_key.return_value = True

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.action == "delete"
        assert result.success is True
        assert result.message == "API key deleted successfully"

        # Verify service calls
        self.api_key_management_service.delete_api_key.assert_called_once_with(
            tenant_id="tenant-123",
            api_key_id="key-789",
        )

    def test_list_api_keys_success(self):
        """Test successful API keys listing."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="list",
        )

        api_keys_data = [
            {
                "id": "key-1",
                "name": "API Key 1",
                "tenant_id": "tenant-123",
                "scopes": ["knowledge_graph:read"],
                "key_prefix": "ak_11111",
                "is_active": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "usage_count": 10,
            },
            {
                "id": "key-2",
                "name": "API Key 2",
                "tenant_id": "tenant-123",
                "scopes": ["ontology:write"],
                "key_prefix": "ak_22222",
                "is_active": False,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "usage_count": 0,
            },
        ]

        self.api_key_management_service.list_api_keys.return_value = api_keys_data

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.action == "list"
        assert result.success is True
        assert len(result.api_keys) == 2
        assert result.api_keys[0].id == "key-1"
        assert result.api_keys[1].id == "key-2"
        assert result.message == "Found 2 API keys"

    def test_rotate_api_key_success(self):
        """Test successful API key rotation."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="rotate",
            api_key_id="key-789",
        )

        existing_key_data = {
            "id": "key-789",
            "name": "Test API Key",
            "tenant_id": "tenant-123",
            "scopes": ["knowledge_graph:read"],
            "key_prefix": "ak_old12",
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "usage_count": 5,
        }

        rotated_key_data = {
            **existing_key_data,
            "key_prefix": "ak_new12",
            "updated_at": datetime.now(),
        }

        self.api_key_management_service.get_api_key.return_value = existing_key_data
        self.api_key_management_service.update_api_key.return_value = rotated_key_data

        # Act
        with patch('secrets.token_hex', return_value='new1234567890abcdef' * 4):
            result = self.use_case.execute(request)

        # Assert
        assert result.action == "rotate"
        assert result.success is True
        assert result.api_key.key_prefix == "ak_new12"
        assert result.full_key == "ak_new1234567890abcdefnew1234567890abcdefnew1234567890abcdefnew1234567890abcdef"
        assert result.message == "API key rotated successfully"

    def test_create_api_key_missing_name(self):
        """Test API key creation with missing name."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="create",
            scopes=["knowledge_graph:read"],
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="API key name is required for creation"):
            self.use_case.execute(request)

    def test_create_api_key_missing_scopes(self):
        """Test API key creation with missing scopes."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="create",
            name="Test API Key",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="API key scopes are required for creation"):
            self.use_case.execute(request)

    def test_create_api_key_past_expiration(self):
        """Test API key creation with past expiration date."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="create",
            name="Test API Key",
            scopes=["knowledge_graph:read"],
            expires_at=datetime.now() - timedelta(days=1),  # Past date
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Expiration date must be in the future"):
            self.use_case.execute(request)

    def test_update_api_key_not_found(self):
        """Test API key update with key not found."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="update",
            api_key_id="key-nonexistent",
            name="Updated Name",
        )

        self.api_key_management_service.get_api_key.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError, match="API key with ID key-nonexistent not found"):
            self.use_case.execute(request)

    def test_delete_api_key_not_found(self):
        """Test API key deletion with key not found."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="delete",
            api_key_id="key-nonexistent",
        )

        self.api_key_management_service.get_api_key.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError, match="API key with ID key-nonexistent not found"):
            self.use_case.execute(request)

    def test_rotate_api_key_not_found(self):
        """Test API key rotation with key not found."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="rotate",
            api_key_id="key-nonexistent",
        )

        self.api_key_management_service.get_api_key.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError, match="API key with ID key-nonexistent not found"):
            self.use_case.execute(request)

    def test_authorization_failure(self):
        """Test API key management with authorization failure."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="create",
            name="Test API Key",
            scopes=["knowledge_graph:read"],
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            "User lacks permission to manage API keys"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError, match="User lacks permission to manage API keys"):
            self.use_case.execute(request)

    def test_validate_input_invalid_action(self):
        """Test validation with invalid action."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="invalid_action",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid action"):
            self.use_case.execute(request)

    def test_validate_input_missing_tenant_id(self):
        """Test validation with missing tenant ID."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="",
            user_id="user-456",
            action="list",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Tenant ID is required"):
            self.use_case.execute(request)

    def test_validate_input_missing_user_id(self):
        """Test validation with missing user ID."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="",
            action="list",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="User ID is required"):
            self.use_case.execute(request)

    def test_validate_input_invalid_scopes(self):
        """Test validation with invalid scopes."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="create",
            name="Test API Key",
            scopes=["invalid:scope", "another:invalid"],
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid scopes"):
            self.use_case.execute(request)

    def test_validate_input_invalid_rate_limit(self):
        """Test validation with invalid rate limit."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="create",
            name="Test API Key",
            scopes=["knowledge_graph:read"],
            rate_limit=0,  # Invalid
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Rate limit must be a positive integer"):
            self.use_case.execute(request)

    def test_update_missing_api_key_id(self):
        """Test update action with missing API key ID."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="update",
            name="Updated Name",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="API key ID is required for update"):
            self.use_case.execute(request)

    def test_delete_missing_api_key_id(self):
        """Test delete action with missing API key ID."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="delete",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="API key ID is required for deletion"):
            self.use_case.execute(request)

    def test_rotate_missing_api_key_id(self):
        """Test rotate action with missing API key ID."""
        # Arrange
        request = ManageAPIKeysRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            action="rotate",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="API key ID is required for rotation"):
            self.use_case.execute(request)

    def test_generate_api_key(self):
        """Test API key generation."""
        # Act
        with patch('secrets.token_hex', return_value='abcdef1234567890' * 4):
            api_key = self.use_case._generate_api_key()

        # Assert
        assert api_key.startswith("ak_")
        assert len(api_key) == 67  # "ak_" + 64 hex characters

    def test_valid_scopes_list(self):
        """Test that valid scopes list contains expected scopes."""
        # Assert
        expected_scopes = [
            "knowledge_graph:read",
            "knowledge_graph:write",
            "ontology:read",
            "ontology:write",
            "user:read",
            "user:write",
            "webhook:read",
            "webhook:write",
            "analytics:read",
            "search:read",
            "workflow:read",
            "workflow:write",
            "admin:read",
            "admin:write",
        ]
        
        assert self.use_case.VALID_SCOPES == expected_scopes

    def test_valid_actions_list(self):
        """Test that valid actions list contains expected actions."""
        # Assert
        expected_actions = ["create", "update", "delete", "list", "rotate"]
        assert self.use_case.VALID_ACTIONS == expected_actions