"""Tests for GetIntegrationStatusUseCase."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from application.ports.base import WebhookRepositoryPort, IntegrationStatusPort
from application.ports.security import AuthorizationPort
from application.use_cases.dto import GetIntegrationStatusRequestDTO
from application.use_cases.webhook.get_integration_status_use_case import GetIntegrationStatusUseCase
from domain.exceptions import ValidationError, AuthorizationError


class TestGetIntegrationStatusUseCase:
    """Test cases for GetIntegrationStatusUseCase."""

    def setup_method(self):
        """Set up test dependencies."""
        self.webhook_repository = Mock(spec=WebhookRepositoryPort)
        self.integration_status_service = Mock(spec=IntegrationStatusPort)
        self.authorization_service = Mock(spec=AuthorizationPort)
        self.use_case = GetIntegrationStatusUseCase(
            webhook_repository=self.webhook_repository,
            integration_status_service=self.integration_status_service,
            authorization_service=self.authorization_service,
        )

    def test_execute_success_all_integrations(self):
        """Test successful integration status check for all integrations."""
        # Arrange
        request = GetIntegrationStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
        )

        mock_statuses = [
            {
                "integration_type": "webhook",
                "integration_id": "webhook-1",
                "name": "Test Webhook 1",
                "status": "active",
                "last_check_at": datetime(2023, 1, 1, 12, 0, 0),
                "error_message": None,
                "metadata": {"url": "https://example.com/webhook1"},
            },
            {
                "integration_type": "api",
                "integration_id": "api-1",
                "name": "External API",
                "status": "active",
                "last_check_at": datetime(2023, 1, 1, 12, 5, 0),
                "error_message": None,
                "metadata": {"endpoint": "https://api.example.com"},
            },
            {
                "integration_type": "webhook",
                "integration_id": "webhook-2",
                "name": "Test Webhook 2",
                "status": "error",
                "last_check_at": datetime(2023, 1, 1, 11, 30, 0),
                "error_message": "Connection timeout",
                "metadata": {"url": "https://example.com/webhook2"},
            },
        ]

        self.integration_status_service.check_integration_status.return_value = mock_statuses

        # Act
        with patch('datetime.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 10, 0)
            mock_datetime.now.return_value = mock_now
            result = self.use_case.execute(request)

        # Assert
        assert len(result.integrations) == 3
        assert result.overall_status == "degraded"  # One error out of 3
        assert result.total_integrations == 3
        assert result.active_integrations == 2
        assert result.failed_integrations == 1
        assert result.checked_at == mock_now

        # Check individual integrations
        webhook_1 = next(i for i in result.integrations if i.integration_id == "webhook-1")
        assert webhook_1.integration_type == "webhook"
        assert webhook_1.name == "Test Webhook 1"
        assert webhook_1.status == "active"
        assert webhook_1.error_message is None

        webhook_2 = next(i for i in result.integrations if i.integration_id == "webhook-2")
        assert webhook_2.status == "error"
        assert webhook_2.error_message == "Connection timeout"

        # Verify authorization check
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-456",
            resource_type="integration",
            action="read",
            tenant_id="tenant-123",
        )

        # Verify service call
        self.integration_status_service.check_integration_status.assert_called_once_with(
            tenant_id="tenant-123",
            integration_type=None,
        )

    def test_execute_success_filtered_by_type(self):
        """Test successful integration status check filtered by type."""
        # Arrange
        request = GetIntegrationStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            integration_type="webhook",
        )

        mock_statuses = [
            {
                "integration_type": "webhook",
                "integration_id": "webhook-1",
                "name": "Test Webhook 1",
                "status": "active",
                "last_check_at": datetime(2023, 1, 1, 12, 0, 0),
                "metadata": {},
            },
        ]

        self.integration_status_service.check_integration_status.return_value = mock_statuses

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert len(result.integrations) == 1
        assert result.integrations[0].integration_type == "webhook"

        # Verify service call with filter
        self.integration_status_service.check_integration_status.assert_called_once_with(
            tenant_id="tenant-123",
            integration_type="webhook",
        )

    def test_execute_empty_integrations(self):
        """Test integration status check with no integrations."""
        # Arrange
        request = GetIntegrationStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
        )

        self.integration_status_service.check_integration_status.return_value = []

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert len(result.integrations) == 0
        assert result.overall_status == "healthy"
        assert result.total_integrations == 0
        assert result.active_integrations == 0
        assert result.failed_integrations == 0

    def test_execute_authorization_failure(self):
        """Test integration status check with authorization failure."""
        # Arrange
        request = GetIntegrationStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            "User lacks permission to read integrations"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError, match="User lacks permission to read integrations"):
            self.use_case.execute(request)

        # Verify service was not called
        self.integration_status_service.check_integration_status.assert_not_called()

    def test_validate_input_missing_tenant_id(self):
        """Test validation with missing tenant ID."""
        # Arrange
        request = GetIntegrationStatusRequestDTO(
            tenant_id="",
            user_id="user-456",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Tenant ID is required"):
            self.use_case.execute(request)

    def test_validate_input_missing_user_id(self):
        """Test validation with missing user ID."""
        # Arrange
        request = GetIntegrationStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="User ID is required"):
            self.use_case.execute(request)

    def test_validate_input_invalid_integration_type(self):
        """Test validation with invalid integration type."""
        # Arrange
        request = GetIntegrationStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            integration_type="invalid_type",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid integration type"):
            self.use_case.execute(request)

    def test_calculate_overall_status_healthy(self):
        """Test overall status calculation for healthy state."""
        # Arrange
        from application.use_cases.dto import IntegrationStatusDTO
        integrations = [
            IntegrationStatusDTO(
                integration_type="webhook",
                integration_id="1",
                name="Test 1",
                status="active",
            ),
            IntegrationStatusDTO(
                integration_type="api",
                integration_id="2",
                name="Test 2",
                status="active",
            ),
        ]

        # Act
        status = self.use_case._calculate_overall_status(integrations)

        # Assert
        assert status == "healthy"

    def test_calculate_overall_status_degraded_with_errors(self):
        """Test overall status calculation for degraded state with errors."""
        # Arrange
        from application.use_cases.dto import IntegrationStatusDTO
        integrations = [
            IntegrationStatusDTO(
                integration_type="webhook",
                integration_id="1",
                name="Test 1",
                status="active",
            ),
            IntegrationStatusDTO(
                integration_type="api",
                integration_id="2",
                name="Test 2",
                status="error",
            ),
            IntegrationStatusDTO(
                integration_type="webhook",
                integration_id="3",
                name="Test 3",
                status="active",
            ),
        ]

        # Act
        status = self.use_case._calculate_overall_status(integrations)

        # Assert
        assert status == "degraded"  # 1 error out of 3 (33%)

    def test_calculate_overall_status_critical_with_many_errors(self):
        """Test overall status calculation for critical state with many errors."""
        # Arrange
        from application.use_cases.dto import IntegrationStatusDTO
        integrations = [
            IntegrationStatusDTO(
                integration_type="webhook",
                integration_id="1",
                name="Test 1",
                status="error",
            ),
            IntegrationStatusDTO(
                integration_type="api",
                integration_id="2",
                name="Test 2",
                status="error",
            ),
        ]

        # Act
        status = self.use_case._calculate_overall_status(integrations)

        # Assert
        assert status == "critical"  # 2 errors out of 2 (100%)

    def test_calculate_overall_status_degraded_with_inactive(self):
        """Test overall status calculation for degraded state with inactive integrations."""
        # Arrange
        from application.use_cases.dto import IntegrationStatusDTO
        integrations = [
            IntegrationStatusDTO(
                integration_type="webhook",
                integration_id="1",
                name="Test 1",
                status="active",
            ),
            IntegrationStatusDTO(
                integration_type="api",
                integration_id="2",
                name="Test 2",
                status="inactive",
            ),
            IntegrationStatusDTO(
                integration_type="webhook",
                integration_id="3",
                name="Test 3",
                status="inactive",
            ),
        ]

        # Act
        status = self.use_case._calculate_overall_status(integrations)

        # Assert
        assert status == "degraded"  # 2 inactive out of 3 (67% > 30%)

    def test_calculate_overall_status_empty_list(self):
        """Test overall status calculation for empty integration list."""
        # Act
        status = self.use_case._calculate_overall_status([])

        # Assert
        assert status == "healthy"