"""Tests for the backup system data use case."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from domain.entities import GraphBackup
from application.exceptions import ValidationError, ApplicationError
from application.use_cases.system.backup_system_data_use_case import (
    BackupSystemDataUseCase,
    BackupSystemDataRequest,
    BackupSystemDataResponse,
)


class TestBackupSystemDataUseCase:
    """Test suite for the backup system data use case."""

    def setup_method(self):
        """Set up test dependencies."""
        self.backup_repository = Mock()
        self.storage = Mock()
        self.tracer = Mock()

        # Mock tracer span
        self.mock_span = Mock()
        self.tracer.start_span.return_value.__enter__ = Mock(return_value=self.mock_span)
        self.tracer.start_span.return_value.__exit__ = Mock(return_value=None)

        self.use_case = BackupSystemDataUseCase(
            backup_repository=self.backup_repository,
            storage=self.storage,
            tracer=self.tracer,
        )

    @pytest.fixture
    def anyio_backend(self):
        return "asyncio"

    @pytest.mark.anyio
    async def test_backup_system_data_success(self):
        """Test successful backup creation."""
        # Arrange
        request = BackupSystemDataRequest(
            kg_id="kg1",
            tenant_id="tenant1",
            user_id="user1",
        )

        backup_location = "/tmp/backup1"
        self.storage.create_backup.return_value = backup_location
        
        backup_entity = GraphBackup.create(
            kg_id="kg1", 
            tenant_id="tenant1", 
            location=backup_location
        )
        self.backup_repository.create.return_value = backup_entity

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.backup is not None
        assert response.backup.location == backup_location
        assert response.backup.kg_id == "kg1"
        assert response.backup.tenant_id == "tenant1"
        
        self.storage.create_backup.assert_called_once_with(kg_id="kg1", tenant_id="tenant1")
        self.backup_repository.create.assert_called_once()
        self.tracer.record_metric.assert_called_with(
            name="system_backup_created",
            value=1,
            tenant_id="tenant1",
        )

    @pytest.mark.anyio
    async def test_backup_system_data_validation_error(self):
        """Test validation error handling."""
        # Arrange
        request = BackupSystemDataRequest(
            kg_id="",  # Empty kg_id should trigger validation error
            tenant_id="tenant1",
            user_id="user1",
        )

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Knowledge graph ID is required" in response.error_message
        self.storage.create_backup.assert_not_called()
        self.backup_repository.create.assert_not_called()

    @pytest.mark.anyio
    async def test_backup_system_data_storage_error(self):
        """Test error handling when storage fails."""
        # Arrange
        request = BackupSystemDataRequest(
            kg_id="kg1",
            tenant_id="tenant1",
            user_id="user1",
        )

        self.storage.create_backup.side_effect = Exception("Storage error")

        # Act & Assert
        with pytest.raises(ApplicationError) as exc_info:
            await self.use_case.execute(request)
        
        assert "Failed to backup system data" in str(exc_info.value)
        assert exc_info.value.error_code == "BACKUP_FAILED"
        self.tracer.record_metric.assert_called_with(
            name="system_backup_errors",
            value=1,
            tenant_id="tenant1",
            error_type="Exception",
        )