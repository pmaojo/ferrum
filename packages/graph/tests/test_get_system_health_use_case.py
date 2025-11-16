"""Tests for the get system health use case."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from application.exceptions import ValidationError, AuthorizationError, ApplicationError
from application.ports.health import ComponentHealth, HealthStatus
from application.use_cases.system.get_system_health_use_case import (
    GetSystemHealthUseCase,
    GetSystemHealthRequest,
    GetSystemHealthResponse,
    ComponentHealthDTO,
    SystemHealthDTO,
)


class TestGetSystemHealthUseCase:
    """Test suite for the get system health use case."""

    def setup_method(self):
        """Set up test dependencies."""
        self.health_check_port = Mock()
        self.authorization_port = Mock()
        self.tracer = Mock()

        # Mock tracer span
        self.mock_span = Mock()
        self.tracer.start_span.return_value.__enter__ = Mock(return_value=self.mock_span)
        self.tracer.start_span.return_value.__exit__ = Mock(return_value=None)

        self.use_case = GetSystemHealthUseCase(
            health_check_port=self.health_check_port,
            authorization_port=self.authorization_port,
            tracer=self.tracer,
        )

        # Setup mock component health responses
        self.db_health = ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            details={"connection_pool": 10, "active_connections": 5},
            message="Database is operating normally"
        )
        
        self.cache_health = ComponentHealth(
            name="cache",
            status=HealthStatus.HEALTHY,
            details={"hit_rate": 0.95, "memory_usage": "45%"},
            message="Cache is operating normally"
        )
        
        self.graph_db_health = ComponentHealth(
            name="graph_database",
            status=HealthStatus.HEALTHY,
            details={"nodes": 10000, "relationships": 50000},
            message="Graph database is operating normally"
        )
        
        self.llm_health = ComponentHealth(
            name="llm_service",
            status=HealthStatus.HEALTHY,
            details={"model": "gpt-4", "latency_ms": 250},
            message="LLM service is operating normally"
        )

    @pytest.fixture
    def anyio_backend(self):
        return "asyncio"

    @pytest.mark.anyio
    async def test_get_system_health_all_healthy(self):
        """Test successful health check with all components healthy."""
        # Arrange
        request = GetSystemHealthRequest(
            user_id="admin1",
            include_details=True,
        )

        self.health_check_port.check_database_health.return_value = self.db_health
        self.health_check_port.check_cache_health.return_value = self.cache_health
        self.health_check_port.check_graph_db_health.return_value = self.graph_db_health
        self.health_check_port.check_llm_health.return_value = self.llm_health

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.health is not None
        assert response.health.overall_status == "healthy"
        assert len(response.health.components) == 4
        
        # Check that all components are included
        component_names = [c.name for c in response.health.components]
        assert "database" in component_names
        assert "cache" in component_names
        assert "graph_database" in component_names
        assert "llm_service" in component_names
        
        # Check that details are included
        db_component = next(c for c in response.health.components if c.name == "database")
        assert "connection_pool" in db_component.details
        
        self.authorization_port.check_permission.assert_called_once_with(
            user_id="admin1",
            resource_type="system",
            permission="view_health"
        )
        self.tracer.record_metric.assert_called_with(
            name="system_health_check",
            value=1,
            status="healthy",
        )

    @pytest.mark.anyio
    async def test_get_system_health_degraded(self):
        """Test health check with one degraded component."""
        # Arrange
        request = GetSystemHealthRequest(
            user_id="admin1",
            include_details=False,
        )

        # Make cache degraded
        degraded_cache = ComponentHealth(
            name="cache",
            status=HealthStatus.DEGRADED,
            details={"hit_rate": 0.65, "memory_usage": "85%"},
            message="Cache performance is degraded"
        )

        self.health_check_port.check_database_health.return_value = self.db_health
        self.health_check_port.check_cache_health.return_value = degraded_cache
        self.health_check_port.check_graph_db_health.return_value = self.graph_db_health
        self.health_check_port.check_llm_health.return_value = self.llm_health

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.health is not None
        assert response.health.overall_status == "degraded"
        
        # Check cache component status
        cache_component = next(c for c in response.health.components if c.name == "cache")
        assert cache_component.status == "degraded"
        assert cache_component.message == "Cache performance is degraded"
        
        # Check that details are not included (include_details=False)
        assert not cache_component.details
        
        self.tracer.record_metric.assert_called_with(
            name="system_health_check",
            value=1,
            status="degraded",
        )

    @pytest.mark.anyio
    async def test_get_system_health_critical(self):
        """Test health check with one critical component."""
        # Arrange
        request = GetSystemHealthRequest(
            user_id="admin1",
        )

        # Make database critical
        critical_db = ComponentHealth(
            name="database",
            status=HealthStatus.CRITICAL,
            details={"error": "Connection timeout"},
            message="Database is not responding"
        )

        self.health_check_port.check_database_health.return_value = critical_db
        self.health_check_port.check_cache_health.return_value = self.cache_health
        self.health_check_port.check_graph_db_health.return_value = self.graph_db_health
        self.health_check_port.check_llm_health.return_value = self.llm_health

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.health is not None
        assert response.health.overall_status == "critical"
        
        # Check database component status
        db_component = next(c for c in response.health.components if c.name == "database")
        assert db_component.status == "critical"
        assert db_component.message == "Database is not responding"
        
        self.tracer.record_metric.assert_called_with(
            name="system_health_check",
            value=1,
            status="critical",
        )

    @pytest.mark.anyio
    async def test_get_system_health_authorization_error(self):
        """Test authorization error handling."""
        # Arrange
        request = GetSystemHealthRequest(
            user_id="regular_user",
        )

        self.authorization_port.check_permission.side_effect = AuthorizationError(
            message="Permission denied",
            user_id="regular_user",
            resource_type="system",
            permission="view_health"
        )

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Permission denied" in response.error_message
        assert response.health is None
        
        self.health_check_port.check_database_health.assert_not_called()
        self.tracer.record_metric.assert_called_with(
            name="system_health_check_errors",
            value=1,
            error_type="AuthorizationError",
        )

    @pytest.mark.anyio
    async def test_get_system_health_validation_error(self):
        """Test validation error handling."""
        # Arrange
        request = GetSystemHealthRequest(
            user_id="",  # Empty user_id should trigger validation error
        )

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False
        assert "User ID is required" in response.error_message
        assert response.health is None
        
        self.authorization_port.check_permission.assert_not_called()
        self.health_check_port.check_database_health.assert_not_called()

    @pytest.mark.anyio
    async def test_get_system_health_unexpected_error(self):
        """Test unexpected error handling."""
        # Arrange
        request = GetSystemHealthRequest(
            user_id="admin1",
        )

        self.health_check_port.check_database_health.side_effect = Exception("Unexpected error")

        # Act & Assert
        with pytest.raises(ApplicationError) as exc_info:
            await self.use_case.execute(request)
        
        assert "Failed to get system health" in str(exc_info.value)
        assert exc_info.value.error_code == "HEALTH_CHECK_FAILED"
        self.tracer.record_metric.assert_called_with(
            name="system_health_check_errors",
            value=1,
            error_type="Exception",
        )