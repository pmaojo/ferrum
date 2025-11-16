"""Tests for SyncExternalDataUseCase."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

from application.ports.base import ExternalDataSyncPort
from application.use_cases.knowledge_graph.create_knowledge_graph_use_case import KnowledgeGraphRepositoryPort
from application.ports.security import AuthorizationPort
from application.use_cases.dto import SyncExternalDataRequestDTO
from application.use_cases.webhook.sync_external_data_use_case import SyncExternalDataUseCase
from domain.entities import KnowledgeGraph, ScientificDomain
from domain.exceptions import ValidationError, AuthorizationError, NotFoundError


class TestSyncExternalDataUseCase:
    """Test cases for SyncExternalDataUseCase."""

    def setup_method(self):
        """Set up test dependencies."""
        self.external_data_sync_service = Mock(spec=ExternalDataSyncPort)
        self.kg_repository = Mock(spec=KnowledgeGraphRepositoryPort)
        self.authorization_service = Mock(spec=AuthorizationPort)
        self.use_case = SyncExternalDataUseCase(
            external_data_sync_service=self.external_data_sync_service,
            kg_repository=self.kg_repository,
            authorization_service=self.authorization_service,
        )

    def test_execute_success_api_source(self):
        """Test successful external data sync from API source."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            source_type="api",
            source_config={
                "url": "https://api.example.com/data",
                "method": "GET",
                "headers": {"Authorization": "Bearer token"},
            },
            target_kg_id="kg-789",
            sync_mode="incremental",
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

        # Mock sync result
        sync_result = {
            "sync_id": "sync-123",
            "status": "completed",
            "records_processed": 150,
            "records_imported": 140,
            "records_failed": 10,
            "summary": {"new_entities": 50, "updated_entities": 90},
        }
        self.external_data_sync_service.sync_from_source.return_value = sync_result

        # Act
        with patch('datetime.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            result = self.use_case.execute(request)

        # Assert
        assert result.sync_id == "sync-123"
        assert result.source_type == "api"
        assert result.target_kg_id == "kg-789"
        assert result.sync_mode == "incremental"
        assert result.status == "completed"
        assert result.records_processed == 150
        assert result.records_imported == 140
        assert result.records_failed == 10
        assert result.started_at == mock_now
        assert result.completed_at == mock_now
        assert result.error_message is None
        assert result.summary == {"new_entities": 50, "updated_entities": 90}

        # Verify authorization check
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-456",
            resource_type="knowledge_graph",
            action="update",
            resource_id="kg-789",
            tenant_id="tenant-123",
        )

        # Verify sync service call
        self.external_data_sync_service.sync_from_source.assert_called_once_with(
            source_type="api",
            source_config={
                "url": "https://api.example.com/data",
                "method": "GET",
                "headers": {"Authorization": "Bearer token"},
            },
            target_kg_id="kg-789",
            tenant_id="tenant-123",
            sync_mode="incremental",
            transformation_rules={"field_mapping": {"name": "title"}},
        )

    def test_execute_success_database_source(self):
        """Test successful external data sync from database source."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            source_type="database",
            source_config={
                "connection_string": "postgresql://user:pass@host:5432/db",
                "query": "SELECT * FROM entities WHERE updated_at > ?",
                "parameters": ["2023-01-01"],
            },
            target_kg_id="kg-789",
            sync_mode="delta",
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

        # Mock sync result
        sync_result = {
            "sync_id": "sync-456",
            "status": "completed",
            "records_processed": 50,
            "records_imported": 45,
            "records_failed": 5,
        }
        self.external_data_sync_service.sync_from_source.return_value = sync_result

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.sync_id == "sync-456"
        assert result.source_type == "database"
        assert result.sync_mode == "delta"
        assert result.status == "completed"

    def test_execute_success_file_source(self):
        """Test successful external data sync from file source."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            source_type="file",
            source_config={
                "file_path": "/path/to/data.json",
                "format": "json",
                "encoding": "utf-8",
            },
            target_kg_id="kg-789",
            sync_mode="full",
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

        # Mock sync result
        sync_result = {
            "status": "completed",
            "records_processed": 200,
            "records_imported": 200,
            "records_failed": 0,
        }
        self.external_data_sync_service.sync_from_source.return_value = sync_result

        # Act
        with patch('uuid.uuid4', return_value=uuid4()):
            result = self.use_case.execute(request)

        # Assert
        assert result.source_type == "file"
        assert result.sync_mode == "full"
        assert result.records_failed == 0

    def test_execute_sync_failure(self):
        """Test external data sync with service failure."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            source_type="api",
            source_config={
                "url": "https://api.example.com/data",
                "method": "GET",
            },
            target_kg_id="kg-789",
            sync_mode="incremental",
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

        # Mock sync service exception
        self.external_data_sync_service.sync_from_source.side_effect = Exception("Connection failed")

        # Act
        with patch('datetime.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            result = self.use_case.execute(request)

        # Assert
        assert result.status == "failed"
        assert result.records_processed == 0
        assert result.records_imported == 0
        assert result.records_failed == 0
        assert result.error_message == "Connection failed"
        assert result.started_at == mock_now
        assert result.completed_at == mock_now

    def test_execute_knowledge_graph_not_found(self):
        """Test sync with knowledge graph not found."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            source_type="api",
            source_config={
                "url": "https://api.example.com/data",
                "method": "GET",
            },
            target_kg_id="kg-nonexistent",
            sync_mode="incremental",
        )

        self.kg_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError, match="Knowledge graph with ID kg-nonexistent not found"):
            self.use_case.execute(request)

        # Verify sync service was not called
        self.external_data_sync_service.sync_from_source.assert_not_called()

    def test_execute_authorization_failure(self):
        """Test sync with authorization failure."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            source_type="api",
            source_config={
                "url": "https://api.example.com/data",
                "method": "GET",
            },
            target_kg_id="kg-789",
            sync_mode="incremental",
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            "User lacks permission to update knowledge graph"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError, match="User lacks permission to update knowledge graph"):
            self.use_case.execute(request)

        # Verify repository was not called
        self.kg_repository.get_by_id.assert_not_called()

    def test_validate_input_invalid_source_type(self):
        """Test validation with invalid source type."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            source_type="invalid_type",
            source_config={"url": "https://example.com"},
            target_kg_id="kg-789",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid source type"):
            self.use_case.execute(request)

    def test_validate_input_missing_source_config(self):
        """Test validation with missing source config."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            source_type="api",
            source_config={},
            target_kg_id="kg-789",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Source configuration is required"):
            self.use_case.execute(request)

    def test_validate_input_invalid_sync_mode(self):
        """Test validation with invalid sync mode."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            source_type="api",
            source_config={
                "url": "https://api.example.com/data",
                "method": "GET",
            },
            target_kg_id="kg-789",
            sync_mode="invalid_mode",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid sync mode"):
            self.use_case.execute(request)

    def test_validate_source_config_api_missing_url(self):
        """Test API source config validation with missing URL."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            source_type="api",
            source_config={
                "method": "GET",
            },
            target_kg_id="kg-789",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="API source config missing required field: url"):
            self.use_case.execute(request)

    def test_validate_source_config_api_invalid_method(self):
        """Test API source config validation with invalid HTTP method."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            source_type="api",
            source_config={
                "url": "https://api.example.com/data",
                "method": "INVALID",
            },
            target_kg_id="kg-789",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid HTTP method"):
            self.use_case.execute(request)

    def test_validate_source_config_database_missing_fields(self):
        """Test database source config validation with missing fields."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            source_type="database",
            source_config={
                "connection_string": "postgresql://user:pass@host:5432/db",
                # Missing query
            },
            target_kg_id="kg-789",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Database source config missing required field: query"):
            self.use_case.execute(request)

    def test_validate_source_config_file_invalid_format(self):
        """Test file source config validation with invalid format."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            source_type="file",
            source_config={
                "file_path": "/path/to/data.txt",
                "format": "invalid_format",
            },
            target_kg_id="kg-789",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid file format"):
            self.use_case.execute(request)

    def test_validate_source_config_webhook_missing_fields(self):
        """Test webhook source config validation with missing fields."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            source_type="webhook",
            source_config={
                # Missing webhook_id
            },
            target_kg_id="kg-789",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Webhook source config missing required field: webhook_id"):
            self.use_case.execute(request)

    def test_validate_input_missing_target_kg_id(self):
        """Test validation with missing target knowledge graph ID."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            source_type="api",
            source_config={
                "url": "https://api.example.com/data",
                "method": "GET",
            },
            target_kg_id="",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Target knowledge graph ID is required"):
            self.use_case.execute(request)

    def test_validate_input_missing_tenant_id(self):
        """Test validation with missing tenant ID."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="",
            user_id="user-456",
            source_type="api",
            source_config={
                "url": "https://api.example.com/data",
                "method": "GET",
            },
            target_kg_id="kg-789",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Tenant ID is required"):
            self.use_case.execute(request)

    def test_validate_input_missing_user_id(self):
        """Test validation with missing user ID."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="",
            source_type="api",
            source_config={
                "url": "https://api.example.com/data",
                "method": "GET",
            },
            target_kg_id="kg-789",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="User ID is required"):
            self.use_case.execute(request)

    def test_validate_input_invalid_transformation_rules(self):
        """Test validation with invalid transformation rules."""
        # Arrange
        request = SyncExternalDataRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            source_type="api",
            source_config={
                "url": "https://api.example.com/data",
                "method": "GET",
            },
            target_kg_id="kg-789",
            transformation_rules="not a dict",  # Should be dict
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Transformation rules must be a dictionary"):
            self.use_case.execute(request)