"""Tests for ExportToExternalSystemUseCase."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

from application.ports.base import ExternalDataExportPort
from application.use_cases.knowledge_graph.create_knowledge_graph_use_case import KnowledgeGraphRepositoryPort
from application.ports.security import AuthorizationPort
from application.use_cases.dto import ExportToExternalSystemRequestDTO
from application.use_cases.webhook.export_to_external_system_use_case import ExportToExternalSystemUseCase
from domain.entities import KnowledgeGraph, ScientificDomain
from domain.exceptions import ValidationError, AuthorizationError, NotFoundError


class TestExportToExternalSystemUseCase:
    """Test cases for ExportToExternalSystemUseCase."""

    def setup_method(self):
        """Set up test dependencies."""
        self.external_data_export_service = Mock(spec=ExternalDataExportPort)
        self.kg_repository = Mock(spec=KnowledgeGraphRepositoryPort)
        self.authorization_service = Mock(spec=AuthorizationPort)
        self.use_case = ExportToExternalSystemUseCase(
            external_data_export_service=self.external_data_export_service,
            kg_repository=self.kg_repository,
            authorization_service=self.authorization_service,
        )

    def test_execute_success_api_target(self):
        """Test successful export to API target."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            target_type="api",
            target_config={
                "url": "https://api.example.com/import",
                "method": "POST",
                "headers": {"Authorization": "Bearer token"},
            },
            export_format="json",
            export_filters={"node_types": ["Person", "Organization"]},
            transformation_rules={"field_mapping": {"name": "title"}},
        )

        # Mock knowledge graph
        kg = KnowledgeGraph(
            id="kg-789",
            name="Test KG",
            tenant_id="tenant-123",
            domain=ScientificDomain.GENERAL,
            ontology_version_id="ontology-1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            node_count=100,
            edge_count=200,
        )
        self.kg_repository.get_by_id.return_value = kg

        # Mock export result
        export_result = {
            "export_id": "export-123",
            "status": "completed",
            "records_exported": 150,
            "records_failed": 5,
            "export_location": "https://api.example.com/import/batch-123",
            "summary": {"nodes_exported": 100, "edges_exported": 50},
        }
        self.external_data_export_service.export_to_target.return_value = export_result

        # Act
        with patch('datetime.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            result = self.use_case.execute(request)

        # Assert
        assert result.export_id == "export-123"
        assert result.kg_id == "kg-789"
        assert result.target_type == "api"
        assert result.export_format == "json"
        assert result.status == "completed"
        assert result.records_exported == 150
        assert result.records_failed == 5
        assert result.started_at == mock_now
        assert result.completed_at == mock_now
        assert result.error_message is None
        assert result.export_location == "https://api.example.com/import/batch-123"
        assert result.summary == {"nodes_exported": 100, "edges_exported": 50}

        # Verify authorization check
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-456",
            resource_type="knowledge_graph",
            action="read",
            resource_id="kg-789",
            tenant_id="tenant-123",
        )

        # Verify export service call
        self.external_data_export_service.export_to_target.assert_called_once_with(
            kg_id="kg-789",
            tenant_id="tenant-123",
            target_type="api",
            target_config={
                "url": "https://api.example.com/import",
                "method": "POST",
                "headers": {"Authorization": "Bearer token"},
            },
            export_format="json",
            export_filters={"node_types": ["Person", "Organization"]},
            transformation_rules={"field_mapping": {"name": "title"}},
        )

    def test_execute_success_database_target(self):
        """Test successful export to database target."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            target_type="database",
            target_config={
                "connection_string": "postgresql://user:pass@host:5432/db",
                "table_name": "exported_entities",
                "batch_size": 1000,
            },
            export_format="csv",
        )

        # Mock knowledge graph
        kg = KnowledgeGraph(
            id="kg-789",
            name="Test KG",
            tenant_id="tenant-123",
            domain=ScientificDomain.GENERAL,
            ontology_version_id="ontology-1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            node_count=100,
            edge_count=200,
        )
        self.kg_repository.get_by_id.return_value = kg

        # Mock export result
        export_result = {
            "export_id": "export-456",
            "status": "completed",
            "records_exported": 300,
            "records_failed": 0,
        }
        self.external_data_export_service.export_to_target.return_value = export_result

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.export_id == "export-456"
        assert result.target_type == "database"
        assert result.export_format == "csv"
        assert result.status == "completed"

    def test_execute_success_file_target(self):
        """Test successful export to file target."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            target_type="file",
            target_config={
                "file_path": "/exports/kg-data.rdf",
                "overwrite": True,
            },
            export_format="rdf",
        )

        # Mock knowledge graph
        kg = KnowledgeGraph(
            id="kg-789",
            name="Test KG",
            tenant_id="tenant-123",
            domain=ScientificDomain.GENERAL,
            ontology_version_id="ontology-1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            node_count=100,
            edge_count=200,
        )
        self.kg_repository.get_by_id.return_value = kg

        # Mock export result
        export_result = {
            "status": "completed",
            "records_exported": 200,
            "records_failed": 0,
            "export_location": "/exports/kg-data.rdf",
        }
        self.external_data_export_service.export_to_target.return_value = export_result

        # Act
        with patch('uuid.uuid4', return_value=uuid4()):
            result = self.use_case.execute(request)

        # Assert
        assert result.target_type == "file"
        assert result.export_format == "rdf"
        assert result.export_location == "/exports/kg-data.rdf"

    def test_execute_success_webhook_target(self):
        """Test successful export to webhook target."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            target_type="webhook",
            target_config={
                "webhook_url": "https://example.com/webhook",
                "secret": "webhook-secret",
                "batch_size": 100,
            },
            export_format="json",
        )

        # Mock knowledge graph
        kg = KnowledgeGraph(
            id="kg-789",
            name="Test KG",
            tenant_id="tenant-123",
            domain=ScientificDomain.GENERAL,
            ontology_version_id="ontology-1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            node_count=100,
            edge_count=200,
        )
        self.kg_repository.get_by_id.return_value = kg

        # Mock export result
        export_result = {
            "status": "completed",
            "records_exported": 300,
            "records_failed": 0,
        }
        self.external_data_export_service.export_to_target.return_value = export_result

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.target_type == "webhook"
        assert result.status == "completed"

    def test_execute_export_failure(self):
        """Test export with service failure."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            target_type="api",
            target_config={
                "url": "https://api.example.com/import",
                "method": "POST",
            },
            export_format="json",
        )

        # Mock knowledge graph
        kg = KnowledgeGraph(
            id="kg-789",
            name="Test KG",
            tenant_id="tenant-123",
            domain=ScientificDomain.GENERAL,
            ontology_version_id="ontology-1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            node_count=100,
            edge_count=200,
        )
        self.kg_repository.get_by_id.return_value = kg

        # Mock export service exception
        self.external_data_export_service.export_to_target.side_effect = Exception("Export failed")

        # Act
        with patch('datetime.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            result = self.use_case.execute(request)

        # Assert
        assert result.status == "failed"
        assert result.records_exported == 0
        assert result.records_failed == 0
        assert result.error_message == "Export failed"
        assert result.started_at == mock_now
        assert result.completed_at == mock_now
        assert result.export_location is None

    def test_execute_knowledge_graph_not_found(self):
        """Test export with knowledge graph not found."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-nonexistent",
            target_type="api",
            target_config={
                "url": "https://api.example.com/import",
                "method": "POST",
            },
            export_format="json",
        )

        self.kg_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError, match="Knowledge graph with ID kg-nonexistent not found"):
            self.use_case.execute(request)

        # Verify export service was not called
        self.external_data_export_service.export_to_target.assert_not_called()

    def test_execute_authorization_failure(self):
        """Test export with authorization failure."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            target_type="api",
            target_config={
                "url": "https://api.example.com/import",
                "method": "POST",
            },
            export_format="json",
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            "User lacks permission to read knowledge graph"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError, match="User lacks permission to read knowledge graph"):
            self.use_case.execute(request)

        # Verify repository was not called
        self.kg_repository.get_by_id.assert_not_called()

    def test_validate_input_missing_kg_id(self):
        """Test validation with missing knowledge graph ID."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="",
            target_type="api",
            target_config={
                "url": "https://api.example.com/import",
                "method": "POST",
            },
            export_format="json",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Knowledge graph ID is required"):
            self.use_case.execute(request)

    def test_validate_input_invalid_target_type(self):
        """Test validation with invalid target type."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            target_type="invalid_type",
            target_config={"url": "https://example.com"},
            export_format="json",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid target type"):
            self.use_case.execute(request)

    def test_validate_input_missing_target_config(self):
        """Test validation with missing target config."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            target_type="api",
            target_config={},
            export_format="json",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Target configuration is required"):
            self.use_case.execute(request)

    def test_validate_input_invalid_export_format(self):
        """Test validation with invalid export format."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            target_type="api",
            target_config={
                "url": "https://api.example.com/import",
                "method": "POST",
            },
            export_format="invalid_format",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid export format"):
            self.use_case.execute(request)

    def test_validate_target_config_api_missing_url(self):
        """Test API target config validation with missing URL."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            target_type="api",
            target_config={
                "method": "POST",
            },
            export_format="json",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="API target config missing required field: url"):
            self.use_case.execute(request)

    def test_validate_target_config_api_invalid_method(self):
        """Test API target config validation with invalid HTTP method."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            target_type="api",
            target_config={
                "url": "https://api.example.com/import",
                "method": "GET",  # GET not allowed for export
            },
            export_format="json",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid HTTP method for export"):
            self.use_case.execute(request)

    def test_validate_target_config_database_missing_fields(self):
        """Test database target config validation with missing fields."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            target_type="database",
            target_config={
                "connection_string": "postgresql://user:pass@host:5432/db",
                # Missing table_name
            },
            export_format="csv",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Database target config missing required field: table_name"):
            self.use_case.execute(request)

    def test_validate_target_config_file_missing_fields(self):
        """Test file target config validation with missing fields."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            target_type="file",
            target_config={
                # Missing file_path
            },
            export_format="json",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="File target config missing required field: file_path"):
            self.use_case.execute(request)

    def test_validate_target_config_webhook_missing_fields(self):
        """Test webhook target config validation with missing fields."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            target_type="webhook",
            target_config={
                "webhook_url": "https://example.com/webhook",
                # Missing secret
            },
            export_format="json",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Webhook target config missing required field: secret"):
            self.use_case.execute(request)

    def test_validate_input_missing_tenant_id(self):
        """Test validation with missing tenant ID."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="",
            user_id="user-456",
            kg_id="kg-789",
            target_type="api",
            target_config={
                "url": "https://api.example.com/import",
                "method": "POST",
            },
            export_format="json",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Tenant ID is required"):
            self.use_case.execute(request)

    def test_validate_input_missing_user_id(self):
        """Test validation with missing user ID."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="",
            kg_id="kg-789",
            target_type="api",
            target_config={
                "url": "https://api.example.com/import",
                "method": "POST",
            },
            export_format="json",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="User ID is required"):
            self.use_case.execute(request)

    def test_validate_input_invalid_export_filters(self):
        """Test validation with invalid export filters."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            target_type="api",
            target_config={
                "url": "https://api.example.com/import",
                "method": "POST",
            },
            export_format="json",
            export_filters="not a dict",  # Should be dict
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Export filters must be a dictionary"):
            self.use_case.execute(request)

    def test_validate_input_invalid_transformation_rules(self):
        """Test validation with invalid transformation rules."""
        # Arrange
        request = ExportToExternalSystemRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            target_type="api",
            target_config={
                "url": "https://api.example.com/import",
                "method": "POST",
            },
            export_format="json",
            transformation_rules="not a dict",  # Should be dict
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Transformation rules must be a dictionary"):
            self.use_case.execute(request)