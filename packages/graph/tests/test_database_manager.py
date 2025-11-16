from unittest.mock import MagicMock

from adapters.repositories.database_config import DatabaseConfig, DatabaseManager
from infrastructure.migrations import MigrationManager


def test_create_tables_runs_migrations():
    cfg = DatabaseConfig(host="h", port=5432, database="d", username="u", password="p")
    migration = MagicMock(spec=MigrationManager)
    manager = DatabaseManager(cfg, migration_manager=migration)
    manager.engine = MagicMock()
    manager.session_factory = MagicMock()

    manager.create_tables()

    migration.set_url.assert_called_once_with(cfg.connection_string)
    migration.upgrade.assert_called_once_with()

