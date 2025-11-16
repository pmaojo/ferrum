"""Tests for ExportVisualizationUseCase."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
import base64

from application.ports import TracingPort

from application.use_cases.visualization.export_visualization_use_case import ExportVisualizationUseCase
from application.use_cases.dto import (
    ExportVisualizationRequestDTO,
    VisualizationExportDTO
)
from application.exceptions import ValidationError, NotFoundError, AuthorizationError
from domain.exceptions import VisualizationError


class TestExportVisualizationUseCase:
    """Test cases for ExportVisualizationUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.graph_visualization_port = Mock()
        self.authorization_service = Mock()
        self.tracing_port = Mock(spec=TracingPort)
        self.layout_repository = Mock()

        # Mock tracing context manager
        self.tracing_port.start_span.return_value.__enter__ = Mock()
        self.tracing_port.start_span.return_value.__exit__ = Mock()

        self.use_case = ExportVisualizationUseCase(
            graph_visualization_port=self.graph_visualization_port,
            layout_repository=self.layout_repository,
            authorization_service=self.authorization_service,
            tracing_port=self.tracing_port
        )

    def test_execute_successful_svg_export(self):
        """Test successful SVG export."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="svg",
            width=1920,
            height=1080,
            include_metadata=True
        )

        mock_layout_data = {
            "nodes": [{"id": "node-1", "x": 10, "y": 20}],
            "edges": [{"id": "edge-1", "source": "node-1", "target": "node-2"}]
        }

        mock_export_data = {
            "content": "<svg>...</svg>",
            "size_bytes": 1024,
            "metadata": {
                "format": "svg",
                "created_at": "2023-01-01T00:00:00Z"
            }
        }

        self.graph_visualization_port.generate_layout.return_value = mock_layout_data
        self.graph_visualization_port.export_visualization.return_value = mock_export_data

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert isinstance(result, VisualizationExportDTO)
        assert result.kg_id == "kg-789"
        assert result.tenant_id == "tenant-123"
        assert result.export_format == "svg"
        assert result.file_content == "<svg>...</svg>"
        assert result.file_size_bytes == 1024
        assert result.processing_time_ms > 0
        assert isinstance(result.export_timestamp, datetime)

        # Verify metadata
        assert result.metadata["export_format"] == "svg"
        assert result.metadata["dimensions"]["width"] == 1920
        assert result.metadata["dimensions"]["height"] == 1080
        assert result.metadata["include_metadata"] is True
        assert result.metadata["visualization_id"] == "viz-123"

        # Verify authorization was checked
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-456",
            resource_id="kg-789",
            action="read"
        )

        # Verify visualization port was called
        self.graph_visualization_port.export_visualization.assert_called_once_with(
            kg_id="kg-789",
            tenant_id="tenant-123",
            layout_data=mock_layout_data,
            export_format="svg",
            width=1920,
            height=1080,
            include_metadata=True
        )

        # Verify metrics were recorded
        assert self.tracing_port.record_metric.call_count == 2

    def test_execute_successful_png_export_with_binary_content(self):
        """Test successful PNG export with binary content."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="png",
            width=800,
            height=600
        )

        # Mock binary PNG content
        binary_content = b'\x89PNG\r\n\x1a\n...'  # Fake PNG header
        expected_base64 = base64.b64encode(binary_content).decode('utf-8')

        mock_layout_data = {"nodes": [], "edges": []}
        mock_export_data = {
            "content": binary_content,
            "size_bytes": len(binary_content),
            "metadata": {"format": "png"}
        }

        self.graph_visualization_port.generate_layout.return_value = mock_layout_data
        self.graph_visualization_port.export_visualization.return_value = mock_export_data

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.export_format == "png"
        assert result.file_content == expected_base64
        assert result.file_size_bytes == len(binary_content)

    def test_execute_successful_json_export(self):
        """Test successful JSON export."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="json"
        )

        mock_layout_data = {"nodes": [], "edges": []}
        mock_export_data = {
            "content": '{"nodes": [], "edges": []}',
            "size_bytes": 25,
            "metadata": {"format": "json"}
        }

        self.graph_visualization_port.generate_layout.return_value = mock_layout_data
        self.graph_visualization_port.export_visualization.return_value = mock_export_data

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.export_format == "json"
        assert result.file_content == '{"nodes": [], "edges": []}'
        # JSON format should not have dimensions in metadata
        assert result.metadata["dimensions"] is None

    def test_execute_with_missing_kg_id(self):
        """Test execution with missing knowledge graph ID."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="",  # Empty kg_id
            visualization_id="viz-123",
            export_format="svg"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Knowledge graph ID is required" in str(exc_info.value)

    def test_execute_with_missing_visualization_id(self):
        """Test execution with missing visualization ID."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="",  # Empty visualization_id
            export_format="svg"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Visualization ID is required" in str(exc_info.value)

    def test_execute_with_unsupported_format(self):
        """Test execution with unsupported export format."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="unsupported_format"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Unsupported export format" in str(exc_info.value)

    def test_execute_with_invalid_width_too_small(self):
        """Test execution with width too small."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="png",
            width=50,  # Too small
            height=600
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Width must be between 100 and 10000 pixels" in str(exc_info.value)

    def test_execute_with_invalid_width_too_large(self):
        """Test execution with width too large."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="svg",
            width=15000,  # Too large
            height=600
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Width must be between 100 and 10000 pixels" in str(exc_info.value)

    def test_execute_with_invalid_height_too_small(self):
        """Test execution with height too small."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="pdf",
            width=800,
            height=50  # Too small
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Height must be between 100 and 10000 pixels" in str(exc_info.value)

    def test_execute_with_authorization_failure(self):
        """Test execution when authorization fails."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="svg"
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            "User does not have permission to read knowledge graph"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError):
            self.use_case.execute(request)

    def test_execute_with_visualization_failure(self):
        """Test execution when visualization port fails."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="svg"
        )

        self.graph_visualization_port.generate_layout.side_effect = Exception(
            "Layout generation failed"
        )

        # Act & Assert
        with pytest.raises(VisualizationError) as exc_info:
            self.use_case.execute(request)

        assert "Visualization export failed" in str(exc_info.value)

    def test_execute_with_export_failure(self):
        """Test execution when export fails."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="svg"
        )

        mock_layout_data = {"nodes": [], "edges": []}
        self.graph_visualization_port.generate_layout.return_value = mock_layout_data
        self.graph_visualization_port.export_visualization.side_effect = Exception(
            "Export failed"
        )

        # Act & Assert
        with pytest.raises(VisualizationError) as exc_info:
            self.use_case.execute(request)

        assert "Visualization export failed" in str(exc_info.value)

    def test_supported_formats_validation(self):
        """Test that all supported formats are accepted."""
        supported_formats = [
            "svg", "png", "pdf", "json", "graphml", "gexf", "dot", "cypher"
        ]

        for export_format in supported_formats:
            request = ExportVisualizationRequestDTO(
                tenant_id="tenant-123",
                user_id="user-456",
                kg_id="kg-789",
                visualization_id="viz-123",
                export_format=export_format
            )

            # Should not raise ValidationError
            self.use_case._validate_request(request)

    def test_convert_export_to_dto_with_string_binary_content(self):
        """Test conversion when binary content is already a string."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="png"
        )

        # Mock export data with string content (already base64)
        base64_content = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        export_data = {
            "content": base64_content,
            "size_bytes": 100,
            "metadata": {}
        }

        # Act
        result = self.use_case._convert_export_to_dto(export_data, request)

        # Assert
        assert result.file_content == base64_content  # Should remain unchanged

    def test_convert_export_to_dto_non_binary_format(self):
        """Test conversion for non-binary format."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="svg"
        )

        export_data = {
            "content": "<svg>content</svg>",
            "size_bytes": 18,
            "metadata": {"format": "svg"}
        }

        # Act
        result = self.use_case._convert_export_to_dto(export_data, request)

        # Assert
        assert result.file_content == "<svg>content</svg>"  # Should remain unchanged
        assert result.file_size_bytes == 18
        assert result.metadata["format"] == "svg"

    def test_convert_export_to_dto_missing_fields(self):
        """Test conversion with missing fields in export data."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="json"
        )

        export_data = {}  # Empty export data

        # Act
        result = self.use_case._convert_export_to_dto(export_data, request)

        # Assert
        assert result.file_content == ""
        assert result.file_size_bytes == 0  # Length of empty string
        assert result.metadata["export_format"] == "json"
        assert result.metadata["visualization_id"] == "viz-123"

    def test_get_or_generate_layout_data_generates_when_missing(self):
        """Generate layout when repository has no data."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="svg"
        )

        mock_layout_data = {"nodes": [], "edges": []}
        self.layout_repository.get_layout.return_value = None
        self.graph_visualization_port.generate_layout.return_value = mock_layout_data

        # Act
        result = self.use_case._get_or_generate_layout_data(request)

        # Assert
        assert result == mock_layout_data

        # Verify generate_layout was called with default parameters
        self.graph_visualization_port.generate_layout.assert_called_once_with(
            kg_id="kg-789",
            tenant_id="tenant-123",
            algorithm="force_directed",
            node_limit=1000,
            include_communities=False,
            filters={}
        )

    def test_get_or_generate_layout_data_uses_existing_layout(self):
        """Return cached layout when available."""
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-999",
            export_format="svg"
        )

        mock_layout_data = {"nodes": [1], "edges": [2]}
        self.layout_repository.get_layout.return_value = mock_layout_data

        result = self.use_case._get_or_generate_layout_data(request)

        assert result == mock_layout_data
        self.graph_visualization_port.generate_layout.assert_not_called()

    def test_tracing_span_creation(self):
        """Test that tracing span is created correctly."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="graphml"
        )

        mock_layout_data = {"nodes": [], "edges": []}
        mock_export_data = {"content": "", "size_bytes": 0, "metadata": {}}

        self.graph_visualization_port.generate_layout.return_value = mock_layout_data
        self.graph_visualization_port.export_visualization.return_value = mock_export_data

        # Act
        self.use_case.execute(request)

        # Assert
        self.tracing_port.start_span.assert_called_once_with(
            name="export_visualization",
            tenant_id="tenant-123",
            kg_id="kg-789",
            export_format="graphml"
        )

    def test_execute_with_default_dimensions(self):
        """Test execution with default dimensions."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="svg"
            # Using default width=1920, height=1080
        )

        mock_layout_data = {"nodes": [], "edges": []}
        mock_export_data = {"content": "", "size_bytes": 0, "metadata": {}}

        self.graph_visualization_port.generate_layout.return_value = mock_layout_data
        self.graph_visualization_port.export_visualization.return_value = mock_export_data

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.metadata["dimensions"]["width"] == 1920
        assert result.metadata["dimensions"]["height"] == 1080

    def test_execute_without_metadata(self):
        """Test execution with include_metadata=False."""
        # Arrange
        request = ExportVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-123",
            export_format="svg",
            include_metadata=False
        )

        mock_layout_data = {"nodes": [], "edges": []}
        mock_export_data = {"content": "", "size_bytes": 0, "metadata": {}}

        self.graph_visualization_port.generate_layout.return_value = mock_layout_data
        self.graph_visualization_port.export_visualization.return_value = mock_export_data

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.metadata["include_metadata"] is False

        # Verify export was called with include_metadata=False
        self.graph_visualization_port.export_visualization.assert_called_once()
        call_args = self.graph_visualization_port.export_visualization.call_args
        assert call_args[1]["include_metadata"] is False