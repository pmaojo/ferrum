"""Tests for CreateWebhookUseCase."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

from application.ports.base import WebhookRepositoryPort
from application.ports.security import AuthorizationPort
from application.use_cases.dto import CreateWebhookRequestDTO
from application.use_cases.webhook.create_webhook_use_case import CreateWebhookUseCase
from domain.entities import Webhook, WebhookStatus
from domain.exceptions import ValidationError, AuthorizationError


class TestCreateWebhookUseCase:
    """Test cases for CreateWebhookUseCase."""

    def setup_method(self):
        """Set up test dependencies."""
        self.webhook_repository = Mock(spec=WebhookRepositoryPort)
        self.authorization_service = Mock(spec=AuthorizationPort)
        self.use_case = CreateWebhookUseCase(
            webhook_repository=self.webhook_repository,
            authorization_service=self.authorization_service,
        )

    async def test_execute_success(self):
        """Test successful webhook creation."""
        # Arrange
        request = CreateWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["knowledge_graph.created", "ontology.updated"],
            description="Test webhook description",
            is_active=True,
        )

        created_webhook = Webhook(
            id="webhook-789",
            tenant_id=request.tenant_id,
            url=request.url,
            events=request.events,
            secret="generated-secret",
            status=WebhookStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.webhook_repository.create.return_value = created_webhook

        # Act
        with patch('secrets.token_hex', return_value='generated-secret'):
            result = self.use_case.execute(request)

        # Assert
        assert result.id == "webhook-789"
        assert result.name == "Test Webhook"
        assert result.url == "https://example.com/webhook"
        assert result.events == ["knowledge_graph.created", "ontology.updated"]
        assert result.tenant_id == "tenant-123"
        assert result.secret == "generated-secret"
        assert result.description == "Test webhook description"
        assert result.is_active is True
        assert result.success_count == 0
        assert result.failure_count == 0

        # Verify authorization check
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-456",
            resource_type="webhook",
            action="create",
            tenant_id="tenant-123",
        )

        # Verify repository call
        self.webhook_repository.create.assert_called_once()
        created_webhook_arg = self.webhook_repository.create.call_args[0][0]
        assert created_webhook_arg.tenant_id == "tenant-123"
        assert created_webhook_arg.url == "https://example.com/webhook"
        assert created_webhook_arg.events == ["knowledge_graph.created", "ontology.updated"]
        assert created_webhook_arg.secret == "generated-secret"
        assert created_webhook_arg.status == WebhookStatus.ACTIVE

    def test_execute_inactive_webhook(self):
        """Test creating an inactive webhook."""
        # Arrange
        request = CreateWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Inactive Webhook",
            url="https://example.com/webhook",
            events=["workflow.completed"],
            is_active=False,
        )

        created_webhook = Webhook(
            id="webhook-789",
            tenant_id=request.tenant_id,
            url=request.url,
            events=request.events,
            secret="generated-secret",
            status=WebhookStatus.INACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.webhook_repository.create.return_value = created_webhook

        # Act
        with patch('secrets.token_hex', return_value='generated-secret'):
            result = self.use_case.execute(request)

        # Assert
        assert result.is_active is False

        # Verify webhook entity has inactive status
        created_webhook_arg = self.webhook_repository.create.call_args[0][0]
        assert created_webhook_arg.status == WebhookStatus.INACTIVE

    def test_execute_authorization_failure(self):
        """Test webhook creation with authorization failure."""
        # Arrange
        request = CreateWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["knowledge_graph.created"],
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            "User lacks permission to create webhooks"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError, match="User lacks permission to create webhooks"):
            self.use_case.execute(request)

        # Verify repository was not called
        self.webhook_repository.create.assert_not_called()

    def test_validate_input_missing_name(self):
        """Test validation with missing name."""
        # Arrange
        request = CreateWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="",
            url="https://example.com/webhook",
            events=["knowledge_graph.created"],
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Webhook name is required"):
            self.use_case.execute(request)

    def test_validate_input_long_name(self):
        """Test validation with name too long."""
        # Arrange
        request = CreateWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="x" * 256,  # Too long
            url="https://example.com/webhook",
            events=["knowledge_graph.created"],
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Webhook name must be 255 characters or less"):
            self.use_case.execute(request)

    def test_validate_input_missing_url(self):
        """Test validation with missing URL."""
        # Arrange
        request = CreateWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Test Webhook",
            url="",
            events=["knowledge_graph.created"],
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Webhook URL is required"):
            self.use_case.execute(request)

    def test_validate_input_invalid_url_format(self):
        """Test validation with invalid URL format."""
        # Arrange
        request = CreateWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Test Webhook",
            url="not-a-valid-url",
            events=["knowledge_graph.created"],
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid webhook URL format"):
            self.use_case.execute(request)

    def test_validate_input_invalid_url_scheme(self):
        """Test validation with invalid URL scheme."""
        # Arrange
        request = CreateWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Test Webhook",
            url="ftp://example.com/webhook",
            events=["knowledge_graph.created"],
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Webhook URL must use HTTP or HTTPS"):
            self.use_case.execute(request)

    def test_validate_input_missing_events(self):
        """Test validation with missing events."""
        # Arrange
        request = CreateWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Test Webhook",
            url="https://example.com/webhook",
            events=[],
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="At least one webhook event is required"):
            self.use_case.execute(request)

    def test_validate_input_invalid_events(self):
        """Test validation with invalid events."""
        # Arrange
        request = CreateWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["invalid.event", "another.invalid"],
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid webhook events"):
            self.use_case.execute(request)

    def test_validate_input_mixed_valid_invalid_events(self):
        """Test validation with mix of valid and invalid events."""
        # Arrange
        request = CreateWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["knowledge_graph.created", "invalid.event"],
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid webhook events: invalid.event"):
            self.use_case.execute(request)

    def test_validate_input_missing_tenant_id(self):
        """Test validation with missing tenant ID."""
        # Arrange
        request = CreateWebhookRequestDTO(
            tenant_id="",
            user_id="user-456",
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["knowledge_graph.created"],
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Tenant ID is required"):
            self.use_case.execute(request)

    def test_validate_input_missing_user_id(self):
        """Test validation with missing user ID."""
        # Arrange
        request = CreateWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="",
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["knowledge_graph.created"],
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="User ID is required"):
            self.use_case.execute(request)

    def test_generate_webhook_secret(self):
        """Test webhook secret generation."""
        # Act
        secret = self.use_case._generate_webhook_secret()

        # Assert
        assert isinstance(secret, str)
        assert len(secret) == 64  # 32 bytes * 2 (hex encoding)

    def test_valid_webhook_events_list(self):
        """Test that valid webhook events list contains expected events."""
        # Assert
        expected_events = [
            "knowledge_graph.created",
            "knowledge_graph.updated",
            "knowledge_graph.deleted",
            "ontology.created",
            "ontology.updated",
            "user.created",
            "user.updated",
            "workflow.completed",
            "workflow.failed",
            "job.completed",
            "job.failed",
            "subscription.created",
            "subscription.updated",
            "subscription.cancelled",
        ]
        
        assert self.use_case.VALID_WEBHOOK_EVENTS == expected_events