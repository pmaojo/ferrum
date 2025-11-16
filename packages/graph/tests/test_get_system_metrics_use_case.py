"""Tests for the get system metrics use case."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from application.exceptions import ValidationError, AuthorizationError, ApplicationError
from application.use_cases.system.get_system_metrics_use_case import (
    GetSystemMetricsUseCase,
    GetSystemMetricsRequest,
    GetSystemMetricsResponse,
    MetricDataPoint,
    MetricSeries,
    SystemMetricsDTO,
)


class TestGetSystemMetricsUseCase:
    """Test suite for the get system metrics use case."""

    def setup_method(self):
        """Set up test dependencies."""
        self.metrics_repository = Mock()
        self.authorization_port = Mock()
        self.tracer = Mock()

        # Mock tracer span
        self.mock_span = Mock()
        self.tracer.start_span.return_value.__enter__ = Mock(return_value=self.mock_span)
        self.tracer.start_span.return_value.__exit__ = Mock(return_value=None)

        self.use_case = GetSystemMetricsUseCase(
            metrics_repository=self.metrics_repository,
            authorization_port=self.authorization_port,
            tracer=self.tracer,
        )

        # Setup mock metric data
        self.now = datetime.utcnow()
        self.one_day_ago = self.now - timedelta(days=1)
        
        # Sample metric data points (timestamp, value)
        self.cpu_data = [
            (self.one_day_ago + timedelta(hours=i), 10 + i % 20)
            for i in range(24)
        ]
        
        self.memory_data = [
            (self.one_day_ago + timedelta(hours=i), 50 + i % 10)
            for i in range(24)
        ]
        
        self.requests_data = [
            (self.one_day_ago + timedelta(hours=i), 100 * (i + 1))
            for i in range(24)
        ]

    @pytest.fixture
    def anyio_backend(self):
        return "asyncio"

    @pytest.mark.anyio
    async def test_get_system_metrics_success(self):
        """Test successful metrics retrieval."""
        # Arrange
        request = GetSystemMetricsRequest(
            user_id="admin1",
            start_time=self.one_day_ago,
            end_time=self.now,
            metrics=["system_cpu_usage", "system_memory_usage", "system_api_requests"],
            aggregation_period="1h",
        )

        # Setup mock repository responses
        self.metrics_repository.query_range.side_effect = lambda **kwargs: {
            "system_cpu_usage": self.cpu_data,
            "system_memory_usage": self.memory_data,
            "system_api_requests": self.requests_data,
        }[kwargs["metric"]]

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.metrics is not None
        assert len(response.metrics.metrics) == 3
        
        # Check that all metrics are included
        metric_names = [m.name for m in response.metrics.metrics]
        assert "system_cpu_usage" in metric_names
        assert "system_memory_usage" in metric_names
        assert "system_api_requests" in metric_names
        
        # Check time range
        assert response.metrics.start_time == self.one_day_ago
        assert response.metrics.end_time == self.now
        assert response.metrics.aggregation_period == "1h"
        
        # Check data points
        cpu_metric = next(m for m in response.metrics.metrics if m.name == "system_cpu_usage")
        assert len(cpu_metric.data_points) == 24
        
        self.authorization_port.check_permission.assert_called_once_with(
            user_id="admin1",
            resource_type="system",
            permission="view_metrics"
        )
        self.tracer.record_metric.assert_called_with(
            name="system_metrics_query",
            value=1,
            metric_count=3,
        )

    @pytest.mark.anyio
    async def test_get_system_metrics_default_time_range(self):
        """Test metrics retrieval with default time range."""
        # Arrange
        request = GetSystemMetricsRequest(
            user_id="admin1",
            metrics=["system_cpu_usage"],
        )

        self.metrics_repository.query_range.return_value = self.cpu_data

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.metrics is not None
        
        # Check that default time range was set
        assert response.metrics.start_time is not None
        assert response.metrics.end_time is not None
        assert (response.metrics.end_time - response.metrics.start_time).total_seconds() == 86400  # 24 hours
        
        # Check that repository was called with correct parameters
        self.metrics_repository.query_range.assert_called_once()
        call_args = self.metrics_repository.query_range.call_args[1]
        assert call_args["metric"] == "system_cpu_usage"
        assert call_args["tenant_id"] == "system"
        assert (call_args["end_time"] - call_args["start_time"]).total_seconds() == 86400  # 24 hours

    @pytest.mark.anyio
    async def test_get_system_metrics_default_metrics(self):
        """Test metrics retrieval with default metrics list."""
        # Arrange
        request = GetSystemMetricsRequest(
            user_id="admin1",
            start_time=self.one_day_ago,
            end_time=self.now,
        )

        # All default metrics should return some data
        self.metrics_repository.query_range.return_value = self.cpu_data

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.metrics is not None
        
        # Check that default metrics were used
        assert len(response.metrics.metrics) > 0
        
        # Check that repository was called multiple times for different metrics
        assert self.metrics_repository.query_range.call_count > 1

    @pytest.mark.anyio
    async def test_get_system_metrics_with_labels(self):
        """Test metrics retrieval with specific labels."""
        # Arrange
        labels = {"component": "api", "environment": "production"}
        request = GetSystemMetricsRequest(
            user_id="admin1",
            start_time=self.one_day_ago,
            end_time=self.now,
            metrics=["system_api_requests"],
            labels=labels,
        )

        self.metrics_repository.query_range.return_value = self.requests_data

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.metrics is not None
        
        # Check that labels were passed to repository
        self.metrics_repository.query_range.assert_called_once()
        call_args = self.metrics_repository.query_range.call_args[1]
        assert call_args["labels"] == labels
        
        # Check that labels are included in the response
        api_metric = response.metrics.metrics[0]
        assert api_metric.labels == labels

    @pytest.mark.anyio
    async def test_get_system_metrics_authorization_error(self):
        """Test authorization error handling."""
        # Arrange
        request = GetSystemMetricsRequest(
            user_id="regular_user",
            metrics=["system_cpu_usage"],
        )

        self.authorization_port.check_permission.side_effect = AuthorizationError(
            message="Permission denied",
            user_id="regular_user",
            resource_type="system",
            permission="view_metrics"
        )

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Permission denied" in response.error_message
        assert response.metrics is None
        
        self.metrics_repository.query_range.assert_not_called()
        self.tracer.record_metric.assert_called_with(
            name="system_metrics_query_errors",
            value=1,
            error_type="AuthorizationError",
        )

    @pytest.mark.anyio
    async def test_get_system_metrics_validation_error(self):
        """Test validation error handling."""
        # Arrange - start time after end time
        request = GetSystemMetricsRequest(
            user_id="admin1",
            start_time=self.now,
            end_time=self.one_day_ago,  # End time before start time
        )

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Start time must be before end time" in response.error_message
        assert response.metrics is None
        
        self.authorization_port.check_permission.assert_not_called()
        self.metrics_repository.query_range.assert_not_called()

    @pytest.mark.anyio
    async def test_get_system_metrics_repository_error(self):
        """Test repository error handling."""
        # Arrange
        request = GetSystemMetricsRequest(
            user_id="admin1",
            metrics=["system_cpu_usage"],
        )

        self.metrics_repository.query_range.side_effect = Exception("Database connection error")

        # Act & Assert
        with pytest.raises(ApplicationError) as exc_info:
            await self.use_case.execute(request)
        
        assert "Failed to get system metrics" in str(exc_info.value)
        assert exc_info.value.error_code == "METRICS_QUERY_FAILED"
        self.tracer.record_metric.assert_called_with(
            name="system_metrics_query_errors",
            value=1,
            error_type="Exception",
        )

    @pytest.mark.anyio
    async def test_get_system_metrics_partial_failure(self):
        """Test handling of partial metric query failures."""
        # Arrange
        request = GetSystemMetricsRequest(
            user_id="admin1",
            metrics=["system_cpu_usage", "system_memory_usage", "invalid_metric"],
        )

        # First metric succeeds, second fails
        def mock_query_range(**kwargs):
            if kwargs["metric"] == "system_cpu_usage":
                return self.cpu_data
            elif kwargs["metric"] == "system_memory_usage":
                return self.memory_data
            else:
                raise Exception(f"Unknown metric: {kwargs['metric']}")
        
        self.metrics_repository.query_range.side_effect = mock_query_range

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.metrics is not None
        
        # Should have two successful metrics
        assert len(response.metrics.metrics) == 2
        
        # Check that error was recorded but execution continued
        self.tracer.record_metric.assert_any_call(
            name="system_metrics_query_errors",
            value=1,
            metric_name="invalid_metric",
            error_type="Exception",
        )