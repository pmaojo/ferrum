"""Alembic migration utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config


class MigrationManager:
    """Wrapper around Alembic commands."""

    def __init__(self, ini_path: Optional[str | Path] = None):
        ini = Path(ini_path or "alembic.ini")
        self.config = Config(str(ini))

    def set_url(self, url: str) -> None:
        """Set the database URL for this migration run."""
        self.config.set_main_option("sqlalchemy.url", url)

    def upgrade(self, revision: str = "head") -> None:
        """Apply migrations up to ``revision``."""
        command.upgrade(self.config, revision)

    def downgrade(self, revision: str = "-1") -> None:
        """Revert migrations down to ``revision``."""
        command.downgrade(self.config, revision)
