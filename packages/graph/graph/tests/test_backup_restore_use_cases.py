"""Tests for backup and restore system data use cases."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from domain.entities import GraphBackup
import importlib.util
import pathlib
import types
import sys

_root = pathlib.Path(__file__).resolve().parents[1] / "application" / "use_cases"

# Load base_use_case and dto without triggering package __init__
base_spec = importlib.util.spec_from_file_location("application.use_cases.base_use_case", _root / "base_use_case.py")
base_module = importlib.util.module_from_spec(base_spec)
base_spec.loader.exec_module(base_module)
sys.modules["application.use_cases.base_use_case"] = base_module

dto_spec = importlib.util.spec_from_file_location("application.use_cases.dto", _root / "dto.py")
dto_module = importlib.util.module_from_spec(dto_spec)
dto_spec.loader.exec_module(dto_module)
sys.modules["application.use_cases.dto"] = dto_module

sys.modules.setdefault("application.use_cases", types.ModuleType("application.use_cases"))

system_path = _root / "system"
backup_spec = importlib.util.spec_from_file_location(
    "application.use_cases.system.backup_system_data_use_case", system_path / "backup_system_data_use_case.py"
)
backup_module = importlib.util.module_from_spec(backup_spec)
backup_spec.loader.exec_module(backup_module)
BackupSystemDataUseCase = backup_module.BackupSystemDataUseCase
BackupSystemDataRequest = backup_module.BackupSystemDataRequest

restore_spec = importlib.util.spec_from_file_location(
    "application.use_cases.system.restore_system_data_use_case", system_path / "restore_system_data_use_case.py"
)
restore_module = importlib.util.module_from_spec(restore_spec)
restore_spec.loader.exec_module(restore_module)
RestoreSystemDataUseCase = restore_module.RestoreSystemDataUseCase
RestoreSystemDataRequest = restore_module.RestoreSystemDataRequest


class TestBackupAndRestoreUseCases:
    """Test suite for backup and restore use cases."""

    def setup_method(self):
        self.backup_repository = Mock()
        self.storage = Mock()
        self.tracer = Mock()

        # Mock tracer span
        self.mock_span = Mock()
        self.tracer.start_span.return_value.__enter__ = Mock(return_value=self.mock_span)
        self.tracer.start_span.return_value.__exit__ = Mock(return_value=None)

        self.backup_use_case = BackupSystemDataUseCase(
            backup_repository=self.backup_repository,
            storage=self.storage,
            tracer=self.tracer,
        )

        self.restore_use_case = RestoreSystemDataUseCase(
            backup_repository=self.backup_repository,
            storage=self.storage,
            tracer=self.tracer,
        )

    @pytest.fixture
    def anyio_backend(self):
        return "asyncio"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_create_backup_success(self):
        request = BackupSystemDataRequest(
            kg_id="kg1",
            tenant_id="tenant1",
            user_id="user1",
        )

        self.storage.create_backup.return_value = "/tmp/backup1"
        backup_entity = GraphBackup.create(kg_id="kg1", tenant_id="tenant1", location="/tmp/backup1")
        self.backup_repository.create.return_value = backup_entity

        response = await self.backup_use_case.execute(request)

        assert response.success is True
        assert response.backup is not None
        assert response.backup.location == "/tmp/backup1"
        self.storage.create_backup.assert_called_once_with(kg_id="kg1", tenant_id="tenant1")
        self.backup_repository.create.assert_called_once()
        self.tracer.record_metric.assert_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_restore_backup_success(self):
        backup_entity = GraphBackup.create(kg_id="kg1", tenant_id="tenant1", location="/tmp/backup1")
        self.backup_repository.get_by_id.return_value = backup_entity

        request = RestoreSystemDataRequest(
            backup_id=backup_entity.id,
            kg_id="kg1",
            tenant_id="tenant1",
            user_id="user1",
        )

        response = await self.restore_use_case.execute(request)

        assert response.success is True
        assert response.restored is True
        self.storage.restore_backup.assert_called_once_with(
            location="/tmp/backup1", kg_id="kg1", tenant_id="tenant1"
        )
        self.tracer.record_metric.assert_called()
