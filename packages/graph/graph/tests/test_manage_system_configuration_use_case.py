"""Tests for the manage system configuration use case."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from application.exceptions import ValidationError, AuthorizationError, ApplicationError
from application.ports.configuration import ConfigurationScope
from application.use_cases.system.manage_system_configuration_use_case import (
    ManageSystemConfigurationUseCase,
    GetSystemConfigurationRequest,
    UpdateSystemConfigurationRequest,
    GetSystemConfigurationResponse,
    UpdateSystemConfigurationResponse,
    SystemConfigurationDTO,
)


class TestManageSystemConfigurationUseCase:
    """Test suite for the manage system configuration use case."""

    def setup_method(self):
        """Set up test dependencies."""
        self.configuration_port = Mock()
        self.authorization_port = Mock()
        self.tracer = Mock()

        # Mock tracer span
        self.mock_span = Mock()
        self.tracer.start_span.return_value.__enter__ = Mock(return_value=self.mock_span)
        self.tracer.start_span.return_value.__exit__ = Mock(return_value=None)

        self.use_case = ManageSystemConfigurationUseCase(
            configuration_port=self.configuration_port,
            authorization_port=self.authorization_port,
            tracer=self.tracer,
        )

        # Sample configuration data
        self.system_config = {
            "database": {
                "connection_pool_size": 20,
                "timeout_seconds": 30
            },
            "cache": {
                "ttl_seconds": 3600,
                "max_size_mb": 512
            },
            "api": {
                "rate_limit": 100,
                "cors_origins": ["https://example.com"]
            }
        }
        
        self.tenant_config = {
            "max_knowledge_graphs": 10,
            "max_storage_gb": 50,
            "features": {
                "advanced_analytics": True,
                "multi_modal": False
            }
        }

    @pytest.fixture
    def anyio_backend(self):
        return "asyncio"

    @pytest.mark.anyio
    async def test_get_system_configuration_success(self):
        """Test successful system configuration retrieval."""
        # Arrange
        request = GetSystemConfigurationRequest(
            user_id="admin1",
            scope="system"
        )

        self.configuration_port.get_configuration.return_value = self.system_config

        # Act
        response = await self.use_case.get_configuration(request)

        # Assert
        assert response.success is True
        assert response.configuration is not None
        assert response.configuration.settings == self.system_config
        assert response.configuration.scope == "system"
        
        self.configuration_port.get_configuration.assert_called_once_with(
            scope=ConfigurationScope.SYSTEM,
            scope_id=None
        )
        
        self.authorization_port.check_permission.assert_called_once_with(
            user_id="admin1",
            resource_type="configuration",
            permission="view_system_configuration"
        )
        
        self.tracer.record_metric.assert_called_with(
            name="system_configuration_get",
            value=1,
            scope="system"
        )

    @pytest.mark.anyio
    async def test_get_tenant_configuration_success(self):
        """Test successful tenant configuration retrieval."""
        # Arrange
        request = GetSystemConfigurationRequest(
            user_id="admin1",
            scope="tenant",
            scope_id="tenant1"
        )

        self.configuration_port.get_configuration.return_value = self.tenant_config

        # Act
        response = await self.use_case.get_configuration(request)

        # Assert
        assert response.success is True
        assert response.configuration is not None
        assert response.configuration.settings == self.tenant_config
        assert response.configuration.scope == "tenant"
        assert response.configuration.scope_id == "tenant1"
        
        self.configuration_port.get_configuration.assert_called_once_with(
            scope=ConfigurationScope.TENANT,
            scope_id="tenant1"
        )
        
        self.authorization_port.check_permission.assert_called_once_with(
            user_id="admin1",
            resource_type="configuration",
            permission="view_tenant_configuration"
        )

    @pytest.mark.anyio
    async def test_get_configuration_invalid_scope(self):
        """Test error handling for invalid scope."""
        # Arrange
        request = GetSystemConfigurationRequest(
            user_id="admin1",
            scope="invalid_scope"  # Invalid scope
        )

        # Act
        response = await self.use_case.get_configuration(request)

        # Assert
        assert response.success is False
        assert "Invalid scope" in response.error_message
        assert response.configuration is None
        
        self.configuration_port.get_configuration.assert_not_called()
        self.authorization_port.check_permission.assert_not_called()

    @pytest.mark.anyio
    async def test_get_configuration_missing_scope_id(self):
        """Test error handling for missing scope ID."""
        # Arrange
        request = GetSystemConfigurationRequest(
            user_id="admin1",
            scope="tenant",  # Tenant scope requires scope_id
            scope_id=None
        )

        # Act
        response = await self.use_case.get_configuration(request)

        # Assert
        assert response.success is False
        assert "Scope ID is required" in response.error_message
        assert response.configuration is None
        
        self.configuration_port.get_configuration.assert_not_called()
        self.authorization_port.check_permission.assert_not_called()

    @pytest.mark.anyio
    async def test_get_configuration_authorization_error(self):
        """Test authorization error handling."""
        # Arrange
        request = GetSystemConfigurationRequest(
            user_id="regular_user",
            scope="system"
        )

        self.authorization_port.check_permission.side_effect = AuthorizationError(
            message="Permission denied",
            user_id="regular_user",
            resource_type="configuration",
            permission="view_system_configuration"
        )

        # Act
        response = await self.use_case.get_configuration(request)

        # Assert
        assert response.success is False
        assert "Permission denied" in response.error_message
        assert response.configuration is None
        
        self.configuration_port.get_configuration.assert_not_called()
        self.tracer.record_metric.assert_called_with(
            name="system_configuration_get_errors",
            value=1,
            error_type="AuthorizationError",
        )

    @pytest.mark.anyio
    async def test_update_system_configuration_success(self):
        """Test successful system configuration update."""
        # Arrange
        new_settings = {
            "database": {
                "connection_pool_size": 30  # Changed from 20 to 30
            },
            "api": {
                "rate_limit": 200  # Changed from 100 to 200
            }
        }
        
        request = UpdateSystemConfigurationRequest(
            user_id="admin1",
            scope="system",
            settings=new_settings
        )

        # No validation errors
        self.configuration_port.validate_configuration.return_value = []
        
        # Return merged configuration
        updated_config = self.system_config.copy()
        updated_config["database"]["connection_pool_size"] = 30
        updated_config["api"]["rate_limit"] = 200
        self.configuration_port.update_configuration.return_value = updated_config

        # Act
        response = await self.use_case.update_configuration(request)

        # Assert
        assert response.success is True
        assert response.configuration is not None
        assert response.configuration.settings == updated_config
        assert response.configuration.scope == "system"
        
        self.configuration_port.validate_configuration.assert_called_once_with(
            scope=ConfigurationScope.SYSTEM,
            settings=new_settings
        )
        
        self.configuration_port.update_configuration.assert_called_once_with(
            scope=ConfigurationScope.SYSTEM,
            settings=new_settings,
            scope_id=None
        )
        
        self.authorization_port.check_permission.assert_called_once_with(
            user_id="admin1",
            resource_type="configuration",
            permission="manage_system_configuration"
        )
        
        self.tracer.record_metric.assert_called_with(
            name="system_configuration_update",
            value=1,
            scope="system",
            setting_count=2  # Two top-level keys in new_settings
        )

    @pytest.mark.anyio
    async def test_update_configuration_validation_errors(self):
        """Test configuration update with validation errors."""
        # Arrange
        invalid_settings = {
            "database": {
                "connection_pool_size": -10  # Invalid negative value
            }
        }
        
        request = UpdateSystemConfigurationRequest(
            user_id="admin1",
            scope="system",
            settings=invalid_settings
        )

        # Return validation errors
        validation_errors = ["connection_pool_size must be a positive integer"]
        self.configuration_port.validate_configuration.return_value = validation_errors

        # Act
        response = await self.use_case.update_configuration(request)

        # Assert
        assert response.success is False
        assert "Configuration validation failed" in response.error_message
        assert response.validation_errors == validation_errors
        assert response.configuration is None
        
        self.configuration_port.validate_configuration.assert_called_once()
        self.configuration_port.update_configuration.assert_not_called()

    @pytest.mark.anyio
    async def test_update_configuration_empty_settings(self):
        """Test error handling for empty settings."""
        # Arrange
        request = UpdateSystemConfigurationRequest(
            user_id="admin1",
            scope="system",
            settings={}  # Empty settings
        )

        # Act
        response = await self.use_case.update_configuration(request)

        # Assert
        assert response.success is False
        assert "Settings cannot be empty" in response.error_message
        assert response.configuration is None
        
        self.configuration_port.validate_configuration.assert_not_called()
        self.configuration_port.update_configuration.assert_not_called()

    @pytest.mark.anyio
    async def test_update_configuration_repository_error(self):
        """Test error handling for repository errors."""
        # Arrange
        request = UpdateSystemConfigurationRequest(
            user_id="admin1",
            scope="system",
            settings={"api": {"rate_limit": 200}}
        )

        # No validation errors
        self.configuration_port.validate_configuration.return_value = []
        
        # Repository error
        self.configuration_port.update_configuration.side_effect = Exception("Database connection error")

        # Act & Assert
        with pytest.raises(ApplicationError) as exc_info:
            await self.use_case.update_configuration(request)
        
        assert "Failed to update system configuration" in str(exc_info.value)
        assert exc_info.value.error_code == "CONFIG_UPDATE_FAILED"
        self.tracer.record_metric.assert_called_with(
            name="system_configuration_update_errors",
            value=1,
            error_type="Exception",
        )