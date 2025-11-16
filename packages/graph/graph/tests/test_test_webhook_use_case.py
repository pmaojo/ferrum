"""Tests for TestWebhookUseCase."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from application.ports.base import WebhookRepositoryPort, WebhookServicePort
from application.ports.security import AuthorizationPort
from application.use_cases.dto import TestWebhookRequestDTO
from application.use_cases.webhook.test_webhook_use_case import TestWebhookUseCase
from domain.entities import Webhook, WebhookStatus
from domain.exceptions import ValidationError, AuthorizationError, NotFoundError


class TestTestWebhookUseCase:
    """Test cases for TestWebhookUseCase."""

    def setup_method(self):
        """Set up test dependencies."""
        self.webhook_repository = Mock(spec=WebhookRepositoryPort)
        self.webhook_service = Mock(spec=WebhookServicePort)
        self.authorization_service = Mock(spec=AuthorizationPort)
        self.use_case = TestWebhookUseCase(
            webhook_repository=self.webhook_repository,
            webhook_service=self.webhook_service,
            authorization_service=self.authorization_service,
        )

    def test_execute_success(self):
        """Test successful webhook testing."""
        # Arrange
        request = TestWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            webhook_id="webhook-789",
            test_event_type="test",
        )

        webhook = Webhook(
            id="webhook-789",
            tenant_id="tenant-123",
            url="https://example.com/webhook",
            events=["knowledge_graph.created"],
            secret="webhook-secret",
            status=WebhookStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.webhook_repository.get_by_id.return_value = webhook
        self.webhook_service.send_test_event.return_value = {
            "success": True,
            "status_code": 200,
            "response_time_ms": 150.5,
        }

        # Act
        with patch('datetime.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            result = self.use_case.execute(request)

        # Assert
        assert result.webhook_id == "webhook-789"
        assert result.test_event_type == "test"
        assert result.success is True
        assert result.response_status == 200
        assert result.response_time_ms == 150.5
        assert result.error_message is None
        assert result.tested_at == mock_now

        # Verify authorization check
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-456",
            resource_type="webhook",
            action="test",
            tenant_id="tenant-123",
        )

        # Verify webhook service call
        self.webhook_service.send_test_event.assert_called_once_with(
            url="https://example.com/webhook",
            secret="webhook-secret",
            event_type="test",
            payload={
                "event_type": "test",
                "timestamp": mock_now.isoformat(),
                "tenant_id": "tenant-123",
                "test": True,
                "message": "This is a test webhook event",
                "webhook_id": "webhook-789",
            },
            timeout=30,
        )

    def test_execute_with_custom_payload(self):
        """Test webhook testing with custom payload."""
        # Arrange
        custom_payload = {"custom": "data", "value": 123}
        request = TestWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            webhook_id="webhook-789",
            test_event_type="custom",
            test_payload=custom_payload,
        )

        webhook = Webhook(
            id="webhook-789",
            tenant_id="tenant-123",
            url="https://example.com/webhook",
            events=["knowledge_graph.created"],
            secret="webhook-secret",
            status=WebhookStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.webhook_repository.get_by_id.return_value = webhook
        self.webhook_service.send_test_event.return_value = {
            "success": True,
            "status_code": 200,
            "response_time_ms": 100.0,
        }

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.success is True

        # Verify custom payload was used
        call_args = self.webhook_service.send_test_event.call_args
        assert call_args[1]["payload"] == custom_payload

    def test_execute_webhook_failure(self):
        """Test webhook testing with webhook failure."""
        # Arrange
        request = TestWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            webhook_id="webhook-789",
            test_event_type="test",
        )

        webhook = Webhook(
            id="webhook-789",
            tenant_id="tenant-123",
            url="https://example.com/webhook",
            events=["knowledge_graph.created"],
            secret="webhook-secret",
            status=WebhookStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.webhook_repository.get_by_id.return_value = webhook
        self.webhook_service.send_test_event.return_value = {
            "success": False,
            "status_code": 500,
            "response_time_ms": 5000.0,
            "error_message": "Internal server error",
        }

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.success is False
        assert result.response_status == 500
        assert result.response_time_ms == 5000.0
        assert result.error_message == "Internal server error"

    def test_execute_service_exception(self):
        """Test webhook testing with service exception."""
        # Arrange
        request = TestWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            webhook_id="webhook-789",
            test_event_type="test",
        )

        webhook = Webhook(
            id="webhook-789",
            tenant_id="tenant-123",
            url="https://example.com/webhook",
            events=["knowledge_graph.created"],
            secret="webhook-secret",
            status=WebhookStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.webhook_repository.get_by_id.return_value = webhook
        self.webhook_service.send_test_event.side_effect = Exception("Connection timeout")

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.success is False
        assert result.response_status is None
        assert result.response_time_ms is None
        assert result.error_message == "Connection timeout"

    def test_execute_webhook_not_found(self):
        """Test webhook testing with webhook not found."""
        # Arrange
        request = TestWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            webhook_id="webhook-789",
            test_event_type="test",
        )

        self.webhook_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError, match="Webhook with ID webhook-789 not found"):
            self.use_case.execute(request)

        # Verify webhook service was not called
        self.webhook_service.send_test_event.assert_not_called()

    def test_execute_webhook_wrong_tenant(self):
        """Test webhook testing with webhook from different tenant."""
        # Arrange
        request = TestWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            webhook_id="webhook-789",
            test_event_type="test",
        )

        webhook = Webhook(
            id="webhook-789",
            tenant_id="different-tenant",  # Different tenant
            url="https://example.com/webhook",
            events=["knowledge_graph.created"],
            secret="webhook-secret",
            status=WebhookStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.webhook_repository.get_by_id.return_value = webhook

        # Act & Assert
        with pytest.raises(NotFoundError, match="Webhook with ID webhook-789 not found"):
            self.use_case.execute(request)

    def test_execute_authorization_failure(self):
        """Test webhook testing with authorization failure."""
        # Arrange
        request = TestWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            webhook_id="webhook-789",
            test_event_type="test",
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            "User lacks permission to test webhooks"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError, match="User lacks permission to test webhooks"):
            self.use_case.execute(request)

        # Verify repository was not called
        self.webhook_repository.get_by_id.assert_not_called()

    def test_validate_input_missing_webhook_id(self):
        """Test validation with missing webhook ID."""
        # Arrange
        request = TestWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            webhook_id="",
            test_event_type="test",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Webhook ID is required"):
            self.use_case.execute(request)

    def test_validate_input_missing_test_event_type(self):
        """Test validation with missing test event type."""
        # Arrange
        request = TestWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            webhook_id="webhook-789",
            test_event_type="",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Test event type is required"):
            self.use_case.execute(request)

    def test_validate_input_missing_tenant_id(self):
        """Test validation with missing tenant ID."""
        # Arrange
        request = TestWebhookRequestDTO(
            tenant_id="",
            user_id="user-456",
            webhook_id="webhook-789",
            test_event_type="test",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Tenant ID is required"):
            self.use_case.execute(request)

    def test_validate_input_missing_user_id(self):
        """Test validation with missing user ID."""
        # Arrange
        request = TestWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="",
            webhook_id="webhook-789",
            test_event_type="test",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="User ID is required"):
            self.use_case.execute(request)

    def test_create_test_payload_knowledge_graph_event(self):
        """Test creating test payload for knowledge graph event."""
        # Arrange
        request = TestWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            webhook_id="webhook-789",
            test_event_type="knowledge_graph.created",
        )

        # Act
        with patch('datetime.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            payload = self.use_case._create_test_payload(request)

        # Assert
        assert payload["event_type"] == "knowledge_graph.created"
        assert payload["timestamp"] == mock_now.isoformat()
        assert payload["tenant_id"] == "tenant-123"
        assert payload["test"] is True
        assert "knowledge_graph" in payload
        assert payload["knowledge_graph"]["id"] == "test-kg-123"
        assert payload["knowledge_graph"]["tenant_id"] == "tenant-123"

    def test_create_test_payload_ontology_event(self):
        """Test creating test payload for ontology event."""
        # Arrange
        request = TestWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            webhook_id="webhook-789",
            test_event_type="ontology.updated",
        )

        # Act
        payload = self.use_case._create_test_payload(request)

        # Assert
        assert payload["event_type"] == "ontology.updated"
        assert "ontology" in payload
        assert payload["ontology"]["id"] == "test-ontology-123"
        assert payload["ontology"]["version"] == "1.0.0"

    def test_create_test_payload_workflow_event(self):
        """Test creating test payload for workflow event."""
        # Arrange
        request = TestWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            webhook_id="webhook-789",
            test_event_type="workflow.completed",
        )

        # Act
        payload = self.use_case._create_test_payload(request)

        # Assert
        assert payload["event_type"] == "workflow.completed"
        assert "job" in payload
        assert payload["job"]["status"] == "completed"

    def test_create_test_payload_user_event(self):
        """Test creating test payload for user event."""
        # Arrange
        request = TestWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            webhook_id="webhook-789",
            test_event_type="user.created",
        )

        # Act
        payload = self.use_case._create_test_payload(request)

        # Assert
        assert payload["event_type"] == "user.created"
        assert "user" in payload
        assert payload["user"]["email"] == "test@example.com"

    def test_create_test_payload_subscription_event(self):
        """Test creating test payload for subscription event."""
        # Arrange
        request = TestWebhookRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            webhook_id="webhook-789",
            test_event_type="subscription.created",
        )

        # Act
        payload = self.use_case._create_test_payload(request)

        # Assert
        assert payload["event_type"] == "subscription.created"
        assert "subscription" in payload
        assert payload["subscription"]["tier"] == "professional"