"""SQLAlchemy-based knowledge graph repository adapter.

This adapter uses SQLAlchemy ORM for database operations, providing
a more Pythonic interface for knowledge graph storage and retrieval.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Index, Integer, String, UniqueConstraint, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

from application.use_cases.dto import SortDirection, SortParams
from application.use_cases.list_knowledge_graphs_use_case import (
    KnowledgeGraphFilterParams,
)
from domain.entities import KnowledgeGraph, ScientificDomain

from .base_knowledge_graph_repository import AbstractKnowledgeGraphRepository

# Configure logging
logger = logging.getLogger(__name__)

# SQLAlchemy base
Base = declarative_base()


class KnowledgeGraphModel(Base):
    """SQLAlchemy model for knowledge graphs table."""

    __tablename__ = "knowledge_graphs"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Basic information
    name = Column(String(255), nullable=False)
    tenant_id = Column(String(36), nullable=False)

    # Scientific domain
    domain = Column(
        SQLEnum(ScientificDomain, name="scientific_domain_enum"), nullable=False
    )

    # Ontology reference
    ontology_version_id = Column(String(36), nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Graph statistics
    node_count = Column(Integer, nullable=False, default=0)
    edge_count = Column(Integer, nullable=False, default=0)

    # Visibility
    is_public = Column(Boolean, nullable=False, default=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint("name", "tenant_id", name="unique_name_per_tenant"),
        CheckConstraint("node_count >= 0", name="check_node_count_positive"),
        CheckConstraint("edge_count >= 0", name="check_edge_count_positive"),
        CheckConstraint("updated_at >= created_at", name="check_valid_timestamps"),
        # Indexes
        Index("idx_kg_tenant_id", "tenant_id"),
        Index("idx_kg_domain", "domain"),
        Index("idx_kg_created_at", "created_at"),
        Index("idx_kg_updated_at", "updated_at"),
        Index("idx_kg_is_public", "is_public"),
        Index("idx_kg_node_count", "node_count"),
        Index("idx_kg_edge_count", "edge_count"),
        Index("idx_kg_tenant_domain", "tenant_id", "domain"),
        Index("idx_kg_tenant_public", "tenant_id", "is_public"),
        Index("idx_kg_tenant_created", "tenant_id", "created_at"),
    )

    def to_domain_entity(self) -> KnowledgeGraph:
        """Convert SQLAlchemy model to domain entity.

        Returns:
            KnowledgeGraph domain entity
        """
        return KnowledgeGraph(
            id=self.id,
            name=self.name,
            tenant_id=self.tenant_id,
            domain=self.domain,
            ontology_version_id=self.ontology_version_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            node_count=self.node_count,
            edge_count=self.edge_count,
            is_public=self.is_public,
        )

    @classmethod
    def from_domain_entity(cls, kg: KnowledgeGraph) -> "KnowledgeGraphModel":
        """Create SQLAlchemy model from domain entity.

        Args:
            kg: KnowledgeGraph domain entity

        Returns:
            KnowledgeGraphModel instance
        """
        return cls(
            id=kg.id,
            name=kg.name,
            tenant_id=kg.tenant_id,
            domain=kg.domain,
            ontology_version_id=kg.ontology_version_id,
            created_at=kg.created_at,
            updated_at=kg.updated_at,
            node_count=kg.node_count,
            edge_count=kg.edge_count,
            is_public=kg.is_public,
        )


class SQLAlchemyKnowledgeGraphRepository(AbstractKnowledgeGraphRepository):
    """SQLAlchemy-based knowledge graph repository implementation."""

    def __init__(self, session: Session):
        """Initialize the repository with a SQLAlchemy session.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def create(self, kg: KnowledgeGraph) -> KnowledgeGraph:
        """Create a new knowledge graph in the database.

        Args:
            kg: Knowledge graph entity to create

        Returns:
            Created knowledge graph entity

        Raises:
            RepositoryError: When creation fails
        """
        logger.info(f"Creating knowledge graph {kg.id} for tenant {kg.tenant_id}")

        try:
            model = KnowledgeGraphModel.from_domain_entity(kg)
            self.session.add(model)
            self.session.commit()

            logger.info(f"Successfully created knowledge graph {kg.id}")
            return model.to_domain_entity()

        except Exception as e:
            self.session.rollback()
            logger.exception(f"Failed to create knowledge graph {kg.id}: {str(e)}")
            raise ValueError(f"Failed to create knowledge graph: {str(e)}")

    def update(self, kg: KnowledgeGraph) -> KnowledgeGraph:
        """Update an existing knowledge graph in the database.

        Args:
            kg: Knowledge graph entity to update

        Returns:
            Updated knowledge graph entity

        Raises:
            RepositoryError: When update fails
        """
        logger.info(f"Updating knowledge graph {kg.id} for tenant {kg.tenant_id}")

        try:
            model = (
                self.session.query(KnowledgeGraphModel)
                .filter(
                    and_(
                        KnowledgeGraphModel.id == kg.id,
                        KnowledgeGraphModel.tenant_id == kg.tenant_id,
                    )
                )
                .first()
            )

            if not model:
                raise ValueError(
                    f"Knowledge graph {kg.id} not found for tenant {kg.tenant_id}"
                )

            # Update fields
            model.name = kg.name
            model.domain = kg.domain
            model.ontology_version_id = kg.ontology_version_id
            model.updated_at = kg.updated_at
            model.node_count = kg.node_count
            model.edge_count = kg.edge_count
            model.is_public = kg.is_public

            self.session.commit()

            logger.info(f"Successfully updated knowledge graph {kg.id}")
            return model.to_domain_entity()

        except Exception as e:
            self.session.rollback()
            logger.exception(f"Failed to update knowledge graph {kg.id}: {str(e)}")
            raise ValueError(f"Failed to update knowledge graph: {str(e)}")

    def get_by_id(self, kg_id: str, tenant_id: str) -> Optional[KnowledgeGraph]:
        """Get knowledge graph by ID and tenant.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Returns:
            Knowledge graph entity if found, None otherwise
        """
        logger.info(f"Retrieving knowledge graph {kg_id} for tenant {tenant_id}")

        try:
            model = (
                self.session.query(KnowledgeGraphModel)
                .filter(
                    and_(
                        KnowledgeGraphModel.id == kg_id,
                        KnowledgeGraphModel.tenant_id == tenant_id,
                    )
                )
                .first()
            )

            if not model:
                logger.info(f"Knowledge graph {kg_id} not found for tenant {tenant_id}")
                return None

            return model.to_domain_entity()

        except Exception as e:
            logger.exception(f"Failed to retrieve knowledge graph {kg_id}: {str(e)}")
            raise ValueError(f"Failed to retrieve knowledge graph: {str(e)}")

    def get_by_name(self, name: str, tenant_id: str) -> Optional[KnowledgeGraph]:
        """Get knowledge graph by name and tenant.

        Args:
            name: Knowledge graph name
            tenant_id: Tenant identifier

        Returns:
            Knowledge graph entity if found, None otherwise
        """
        logger.info(f"Retrieving knowledge graph '{name}' for tenant {tenant_id}")

        try:
            model = (
                self.session.query(KnowledgeGraphModel)
                .filter(
                    and_(
                        KnowledgeGraphModel.name == name,
                        KnowledgeGraphModel.tenant_id == tenant_id,
                    )
                )
                .first()
            )

            if not model:
                logger.info(
                    f"Knowledge graph '{name}' not found for tenant {tenant_id}"
                )
                return None

            return model.to_domain_entity()

        except Exception as e:
            logger.exception(f"Failed to retrieve knowledge graph '{name}': {str(e)}")
            raise ValueError(f"Failed to retrieve knowledge graph: {str(e)}")

    def list_by_tenant(
        self,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[KnowledgeGraphFilterParams] = None,
        sort: Optional[SortParams] = None,
    ) -> Tuple[List[KnowledgeGraph], int]:
        """List knowledge graphs for a tenant with pagination, filtering, and sorting.

        Args:
            tenant_id: Tenant identifier
            page: Page number (1-based)
            page_size: Number of items per page
            filters: Optional filter parameters
            sort: Optional sort parameters

        Returns:
            Tuple of (knowledge graphs list, total count)
        """
        logger.info(f"Listing knowledge graphs for tenant {tenant_id}, page {page}")

        try:
            # Base query
            query = self.session.query(KnowledgeGraphModel).filter(
                KnowledgeGraphModel.tenant_id == tenant_id
            )

            # Apply filters
            if filters:
                query = self._apply_filters(query, filters)

            # Get total count
            total_count = query.count()

            # Apply sorting
            if sort:
                query = self._apply_sorting(query, sort)
            else:
                query = query.order_by(KnowledgeGraphModel.created_at.desc())

            # Apply pagination
            offset = (page - 1) * page_size
            models = query.offset(offset).limit(page_size).all()

            # Convert to domain entities
            knowledge_graphs = [model.to_domain_entity() for model in models]

            logger.info(
                f"Retrieved {len(knowledge_graphs)} knowledge graphs (total: {total_count})"
            )
            return knowledge_graphs, total_count

        except Exception as e:
            logger.exception(
                f"Failed to list knowledge graphs for tenant {tenant_id}: {str(e)}"
            )
            raise ValueError(f"Failed to list knowledge graphs: {str(e)}")

    def delete_by_id(self, kg_id: str, tenant_id: str) -> bool:
        """Delete a knowledge graph from the database.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Returns:
            True if knowledge graph was deleted, False otherwise
        """
        logger.info(f"Deleting knowledge graph {kg_id} for tenant {tenant_id}")

        try:
            deleted_count = (
                self.session.query(KnowledgeGraphModel)
                .filter(
                    and_(
                        KnowledgeGraphModel.id == kg_id,
                        KnowledgeGraphModel.tenant_id == tenant_id,
                    )
                )
                .delete()
            )

            self.session.commit()

            if deleted_count > 0:
                logger.info(f"Successfully deleted knowledge graph {kg_id}")
                return True
            else:
                logger.info(f"Knowledge graph {kg_id} not found for deletion")
                return False

        except Exception as e:
            self.session.rollback()
            logger.exception(f"Failed to delete knowledge graph {kg_id}: {str(e)}")
            raise ValueError(f"Failed to delete knowledge graph: {str(e)}")

    def _apply_filters(self, query, filters: KnowledgeGraphFilterParams):
        """Apply filters to the query."""

        mapping = self._extract_filters(filters)

        if "domain" in mapping:
            query = query.filter(KnowledgeGraphModel.domain == mapping["domain"])

        if "is_public" in mapping:
            query = query.filter(KnowledgeGraphModel.is_public == mapping["is_public"])

        if "name_contains" in mapping:
            query = query.filter(
                KnowledgeGraphModel.name.ilike(f"%{mapping['name_contains']}%")
            )

        if "min_node_count" in mapping:
            query = query.filter(
                KnowledgeGraphModel.node_count >= mapping["min_node_count"]
            )

        if "max_node_count" in mapping:
            query = query.filter(
                KnowledgeGraphModel.node_count <= mapping["max_node_count"]
            )

        if "min_edge_count" in mapping:
            query = query.filter(
                KnowledgeGraphModel.edge_count >= mapping["min_edge_count"]
            )

        if "max_edge_count" in mapping:
            query = query.filter(
                KnowledgeGraphModel.edge_count <= mapping["max_edge_count"]
            )

        if "created_after" in mapping:
            query = query.filter(
                KnowledgeGraphModel.created_at >= mapping["created_after"]
            )

        if "created_before" in mapping:
            query = query.filter(
                KnowledgeGraphModel.created_at <= mapping["created_before"]
            )

        if "updated_after" in mapping:
            query = query.filter(
                KnowledgeGraphModel.updated_at >= mapping["updated_after"]
            )

        if "updated_before" in mapping:
            query = query.filter(
                KnowledgeGraphModel.updated_at <= mapping["updated_before"]
            )

        return query

    def _apply_sorting(self, query, sort: SortParams):
        """Apply sorting to the query."""

        sort_info = self._resolve_sort(sort)
        mapping = {
            "name": KnowledgeGraphModel.name,
            "created_at": KnowledgeGraphModel.created_at,
            "updated_at": KnowledgeGraphModel.updated_at,
            "node_count": KnowledgeGraphModel.node_count,
            "edge_count": KnowledgeGraphModel.edge_count,
            "domain": KnowledgeGraphModel.domain,
        }

        sort_field = mapping.get(sort_info["field"], KnowledgeGraphModel.created_at)
        if sort_info["direction"] == SortDirection.ASC:
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())
        return query


SQLAlchemyKnowledgeGraphRepository.delete = (
    SQLAlchemyKnowledgeGraphRepository.delete_by_id
)
