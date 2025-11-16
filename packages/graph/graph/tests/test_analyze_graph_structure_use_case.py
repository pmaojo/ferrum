"""Tests for AnalyzeGraphStructureUseCase."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from application.ports import TracingPort

from application.use_cases.analytics.analyze_graph_structure_use_case import (
    AnalyzeGraphStructureUseCase,
)
from application.use_cases.dto import (
    AnalyzeGraphStructureRequestDTO,
    GraphStructureAnalysisDTO,
    GraphMetricDTO
)
from application.exceptions import ValidationError, NotFoundError, AuthorizationError
from domain.exceptions import AnalyticsError


class TestAnalyzeGraphStructureUseCase:
    """Test cases for AnalyzeGraphStructureUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.graph_analytics_port = Mock()
        self.authorization_service = Mock()
        self.tracing_port = Mock(spec=TracingPort)

        # Mock tracing context manager
        self.tracing_port.start_span.return_value.__enter__ = Mock(return_value=None)
        self.tracing_port.start_span.return_value.__exit__ = Mock(return_value=False)

        self.use_case = AnalyzeGraphStructureUseCase(
            graph_analytics_port=self.graph_analytics_port,
            authorization_service=self.authorization_service,
            tracing_port=self.tracing_port
        )

    def test_execute_successful_analysis(self):
        """Test successful graph structure analysis."""
        # Arrange
        request = AnalyzeGraphStructureRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            include_centrality=True,
            include_clustering=True,
            include_connectivity=True
        )

        mock_metrics = {
            "node_count": 100.0,
            "edge_count": 250.0,
            "density": 0.05,
            "average_degree": 5.0,
            "clustering_coefficient": 0.3,
            "diameter": 8.0,
            "average_path_length": 3.2,
            "connected_components": 1.0,
            "largest_component_size": 100.0,
            "assortativity": -0.1,
            "transitivity": 0.25
        }

        self.graph_analytics_port.analyze_structure.return_value = mock_metrics

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert isinstance(result, GraphStructureAnalysisDTO)
        assert result.kg_id == "kg-789"
        assert result.tenant_id == "tenant-123"
        assert len(result.metrics) == 11
        assert result.processing_time_ms > 0
        assert isinstance(result.analysis_timestamp, datetime)

        # Verify authorization was checked
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-456",
            resource_id="kg-789",
            action="read"
        )

        # Verify analytics port was called
        self.graph_analytics_port.analyze_structure.assert_called_once_with(
            kg_id="kg-789",
            tenant_id="tenant-123"
        )

        # Verify metrics were recorded
        self.tracing_port.record_metric.assert_called_once()

    def test_execute_with_missing_kg_id(self):
        """Test execution with missing knowledge graph ID."""
        # Arrange
        request = AnalyzeGraphStructureRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="",  # Empty kg_id
            include_centrality=True
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Knowledge graph ID is required" in str(exc_info.value)

    def test_execute_with_missing_tenant_id(self):
        """Test execution with missing tenant ID."""
        # Arrange
        request = AnalyzeGraphStructureRequestDTO(
            tenant_id="",  # Empty tenant_id
            user_id="user-456",
            kg_id="kg-789"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Tenant ID is required" in str(exc_info.value)

    def test_execute_with_missing_user_id(self):
        """Test execution with missing user ID."""
        # Arrange
        request = AnalyzeGraphStructureRequestDTO(
            tenant_id="tenant-123",
            user_id="",  # Empty user_id
            kg_id="kg-789"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "User ID is required" in str(exc_info.value)

    def test_execute_with_authorization_failure(self):
        """Test execution when authorization fails."""
        # Arrange
        request = AnalyzeGraphStructureRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789"
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            "User does not have permission to read knowledge graph"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError):
            self.use_case.execute(request)

    def test_execute_with_analytics_failure(self):
        """Test execution when analytics port fails."""
        # Arrange
        request = AnalyzeGraphStructureRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789"
        )

        self.graph_analytics_port.analyze_structure.side_effect = Exception(
            "Graph analysis failed"
        )

        # Act & Assert
        with pytest.raises(AnalyticsError) as exc_info:
            self.use_case.execute(request)

        assert "Graph structure analysis failed" in str(exc_info.value)

    def test_convert_metrics_to_dtos(self):
        """Test conversion of metrics data to DTOs."""
        # Arrange
        metrics_data = {
            "node_count": 100.0,
            "edge_count": 250.0,
            "density": 0.05,
            "unknown_metric": 42.0
        }

        # Act
        result = self.use_case._convert_metrics_to_dtos(metrics_data)

        # Assert
        assert len(result) == 4

        # Check known metrics
        node_count_metric = next(m for m in result if m.name == "node_count")
        assert node_count_metric.value == 100.0
        assert node_count_metric.category == "structure"
        assert "Total number of nodes" in node_count_metric.description

        # Check unknown metric
        unknown_metric = next(m for m in result if m.name == "unknown_metric")
        assert unknown_metric.value == 42.0
        assert unknown_metric.category == "other"
        assert "Graph metric: unknown_metric" in unknown_metric.description

    def test_execute_with_minimal_metrics(self):
        """Test execution with minimal metrics data."""
        # Arrange
        request = AnalyzeGraphStructureRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789"
        )

        mock_metrics = {
            "node_count": 10.0,
            "edge_count": 5.0
        }

        self.graph_analytics_port.analyze_structure.return_value = mock_metrics

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert isinstance(result, GraphStructureAnalysisDTO)
        assert len(result.metrics) == 2
        assert result.metrics[0].name in ["node_count", "edge_count"]
        assert result.metrics[1].name in ["node_count", "edge_count"]

    def test_execute_with_empty_metrics(self):
        """Test execution with empty metrics data."""
        # Arrange
        request = AnalyzeGraphStructureRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789"
        )

        self.graph_analytics_port.analyze_structure.return_value = {}

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert isinstance(result, GraphStructureAnalysisDTO)
        assert len(result.metrics) == 0

    def test_tracing_span_creation(self):
        """Test that tracing span is created correctly."""
        # Arrange
        request = AnalyzeGraphStructureRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789"
        )

        self.graph_analytics_port.analyze_structure.return_value = {"node_count": 10.0}

        # Act
        self.use_case.execute(request)

        # Assert
        self.tracing_port.start_span.assert_called_once_with(
            name="analyze_graph_structure",
            tenant_id="tenant-123",
            kg_id="kg-789"
        )

    def test_metric_recording(self):
        """Test that performance metrics are recorded."""
        # Arrange
        request = AnalyzeGraphStructureRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789"
        )

        self.graph_analytics_port.analyze_structure.return_value = {"node_count": 10.0}

        # Act
        self.use_case.execute(request)

        # Assert
        self.tracing_port.record_metric.assert_called_once()
        call_args = self.tracing_port.record_metric.call_args
        assert call_args[1]["name"] == "graph_structure_analysis_duration_ms"
        assert call_args[1]["tenant_id"] == "tenant-123"
        assert "kg_id" in call_args[1]
        assert call_args[1]["value"] > 0