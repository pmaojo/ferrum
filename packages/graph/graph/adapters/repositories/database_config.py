"""Database configuration and connection management.

This module provides database configuration and connection utilities
for the knowledge graph repository adapters.
"""

import os
from typing import Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from infrastructure.migrations import MigrationManager
from application.use_cases.knowledge_graph.create_knowledge_graph_use_case import (
    KnowledgeGraphRepositoryPort,
)


class DatabaseConfig:
    """Database configuration class."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "knowledge_graphs",
        username: str = "postgres",
        password: str = "password",
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
    ):
        """Initialize database configuration.

        Args:
            host: Database host
            port: Database port
            database: Database name
            username: Database username
            password: Database password
            pool_size: Connection pool size
            max_overflow: Maximum pool overflow
            pool_timeout: Pool timeout in seconds
            pool_recycle: Pool recycle time in seconds
        """
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create configuration from environment variables.

        Returns:
            DatabaseConfig instance
        """
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "knowledge_graphs"),
            username=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "password"),
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
        )

    @property
    def connection_string(self) -> str:
        """Get database connection string.

        Returns:
            PostgreSQL connection string
        """
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class DatabaseManager:
    """Database connection and session manager."""

    def __init__(
        self,
        config: DatabaseConfig,
        migration_manager: Optional[MigrationManager] = None,
    ) -> None:
        """Initialize database manager.

        Args:
            config: Database configuration
            migration_manager: Alembic migration helper
        """
        self.config = config
        self.engine: Optional[Engine] = None
        self.session_factory: Optional[sessionmaker] = None
        self.migration_manager = migration_manager or MigrationManager()

    def initialize(self) -> None:
        """Initialize database engine and session factory."""
        self.engine = create_engine(
            self.config.connection_string,
            poolclass=QueuePool,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=self.config.pool_timeout,
            pool_recycle=self.config.pool_recycle,
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
        )

        self.session_factory = sessionmaker(bind=self.engine)

    def create_tables(self) -> None:
        """Create database tables if they don't exist."""
        if not self.engine:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        self.migration_manager.set_url(self.config.connection_string)
        self.migration_manager.upgrade()

    def get_session(self) -> Session:
        """Get a new database session.

        Returns:
            SQLAlchemy session
        """
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        return self.session_factory()

    def get_connection(self):
        """Get a low level database connection."""
        if not self.engine:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.engine.raw_connection()

    def close(self) -> None:
        """Close database connections."""
        if self.engine:
            self.engine.dispose()


def create_db_manager(
    config: DatabaseConfig, migration_manager: Optional[MigrationManager] = None
) -> "DatabaseManager":
    """Factory for ``DatabaseManager`` instances.

    Args:
        config: Database configuration to use.

    Returns:
        Initialized ``DatabaseManager``.
    """
    manager = DatabaseManager(config, migration_manager=migration_manager)
    return manager


def create_knowledge_graph_repository(
    db_manager: DatabaseManager,
    *,
    use_sqlalchemy: Optional[bool] = None,
) -> KnowledgeGraphRepositoryPort:
    """Factory for knowledge graph repository implementations."""
    from .knowledge_graph_repository_adapter import RawSQLKnowledgeGraphRepository
    from .sqlalchemy_knowledge_graph_repository import (
        SQLAlchemyKnowledgeGraphRepository,
    )

    if use_sqlalchemy is None:
        impl = os.getenv("KG_REPOSITORY_IMPL", "sqlalchemy").lower()
        use_sqlalchemy = impl != "raw"

    if use_sqlalchemy:
        return SQLAlchemyKnowledgeGraphRepository(db_manager.get_session())
    return RawSQLKnowledgeGraphRepository(db_manager.get_connection())
