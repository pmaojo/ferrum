"""Database adapter for knowledge graph repository operations.

This adapter provides storage and retrieval of knowledge graphs in a relational database,
supporting multi-tenancy, pagination, filtering, and sorting.
"""

import logging
from datetime import datetime
from typing import Any, List, Optional, Tuple

from application.use_cases.dto import SortDirection, SortParams
from application.use_cases.list_knowledge_graphs_use_case import (
    KnowledgeGraphFilterParams,
)
from domain.entities import KnowledgeGraph

from .base_knowledge_graph_repository import AbstractKnowledgeGraphRepository

# Configure logging
logger = logging.getLogger(__name__)


class RawSQLKnowledgeGraphRepository(AbstractKnowledgeGraphRepository):
    """Database repository for knowledge graph operations.

    This class provides CRUD operations for knowledge graphs with support for
    multi-tenancy, pagination, filtering, and sorting using a relational database.
    """

    def __init__(self, db_connection):
        """Initialize the raw SQL knowledge graph repository.

        Args:
            db_connection: PEP 249 compliant connection
        """
        self.db = db_connection

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
            query = """
                INSERT INTO knowledge_graphs (
                    id, name, tenant_id, domain, ontology_version_id,
                    created_at, updated_at, node_count, edge_count, is_public
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """

            data = self._entity_to_dict(kg)
            values = (
                data["id"],
                data["name"],
                data["tenant_id"],
                data["domain"],
                data["ontology_version_id"],
                data["created_at"],
                data["updated_at"],
                data["node_count"],
                data["edge_count"],
                data["is_public"],
            )

            self.db.execute(query, values)
            self.db.commit()

            logger.info(f"Successfully created knowledge graph {kg.id}")
            return kg

        except Exception as e:
            self.db.rollback()
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
            query = """
                UPDATE knowledge_graphs
                SET name = ?, domain = ?, ontology_version_id = ?,
                    updated_at = ?, node_count = ?, edge_count = ?, is_public = ?
                WHERE id = ? AND tenant_id = ?
            """

            data = self._entity_to_dict(kg)
            values = (
                data["name"],
                data["domain"],
                data["ontology_version_id"],
                data["updated_at"],
                data["node_count"],
                data["edge_count"],
                data["is_public"],
                data["id"],
                data["tenant_id"],
            )

            cursor = self.db.execute(query, values)

            if cursor.rowcount == 0:
                raise ValueError(
                    f"Knowledge graph {kg.id} not found for tenant {kg.tenant_id}"
                )

            self.db.commit()

            logger.info(f"Successfully updated knowledge graph {kg.id}")
            return kg

        except Exception as e:
            self.db.rollback()
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
            query = """
                SELECT id, name, tenant_id, domain, ontology_version_id,
                       created_at, updated_at, node_count, edge_count, is_public
                FROM knowledge_graphs
                WHERE id = ? AND tenant_id = ?
            """

            cursor = self.db.execute(query, (kg_id, tenant_id))
            row = cursor.fetchone()

            if not row:
                logger.info(f"Knowledge graph {kg_id} not found for tenant {tenant_id}")
                return None

            return self._row_to_knowledge_graph(row)

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
            query = """
                SELECT id, name, tenant_id, domain, ontology_version_id,
                       created_at, updated_at, node_count, edge_count, is_public
                FROM knowledge_graphs
                WHERE name = ? AND tenant_id = ?
            """

            cursor = self.db.execute(query, (name, tenant_id))
            row = cursor.fetchone()

            if not row:
                logger.info(
                    f"Knowledge graph '{name}' not found for tenant {tenant_id}"
                )
                return None

            return self._row_to_knowledge_graph(row)

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
            # Build WHERE clause
            where_conditions = ["tenant_id = ?"]
            where_params = [tenant_id]

            if filters:
                where_conditions, where_params = self._build_where_clause(
                    where_conditions, where_params, filters
                )

            where_clause = " AND ".join(where_conditions)

            # Build ORDER BY clause
            order_clause = self._build_order_clause(sort)

            # Count total records
            count_query = f"""
                SELECT COUNT(*) as total
                FROM knowledge_graphs
                WHERE {where_clause}
            """

            cursor = self.db.execute(count_query, where_params)
            total_count = cursor.fetchone()[0]

            # Get paginated results
            offset = (page - 1) * page_size

            list_query = f"""
                SELECT id, name, tenant_id, domain, ontology_version_id,
                       created_at, updated_at, node_count, edge_count, is_public
                FROM knowledge_graphs
                WHERE {where_clause}
                {order_clause}
                LIMIT ? OFFSET ?
            """

            list_params = where_params + [page_size, offset]
            cursor = self.db.execute(list_query, list_params)
            rows = cursor.fetchall()

            knowledge_graphs = [self._row_to_knowledge_graph(row) for row in rows]

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
            query = """
                DELETE FROM knowledge_graphs
                WHERE id = ? AND tenant_id = ?
            """

            cursor = self.db.execute(query, (kg_id, tenant_id))
            deleted = cursor.rowcount > 0

            if deleted:
                self.db.commit()
                logger.info(f"Successfully deleted knowledge graph {kg_id}")
            else:
                logger.info(f"Knowledge graph {kg_id} not found for deletion")

            return deleted

        except Exception as e:
            self.db.rollback()
            logger.exception(f"Failed to delete knowledge graph {kg_id}: {str(e)}")
            raise ValueError(f"Failed to delete knowledge graph: {str(e)}")

    # Backwards compatibility
    delete = delete_by_id

    def _build_where_clause(
        self,
        conditions: List[str],
        params: List[Any],
        filters: KnowledgeGraphFilterParams,
    ) -> Tuple[List[str], List[Any]]:
        """Build WHERE clause conditions and parameters from filters."""

        mapping = self._extract_filters(filters)

        if "domain" in mapping:
            conditions.append("domain = ?")
            params.append(mapping["domain"])

        if "is_public" in mapping:
            conditions.append("is_public = ?")
            params.append(mapping["is_public"])

        if "name_contains" in mapping:
            conditions.append("name ILIKE ?")
            params.append(f"%{mapping['name_contains']}%")

        if "min_node_count" in mapping:
            conditions.append("node_count >= ?")
            params.append(mapping["min_node_count"])

        if "max_node_count" in mapping:
            conditions.append("node_count <= ?")
            params.append(mapping["max_node_count"])

        if "min_edge_count" in mapping:
            conditions.append("edge_count >= ?")
            params.append(mapping["min_edge_count"])

        if "max_edge_count" in mapping:
            conditions.append("edge_count <= ?")
            params.append(mapping["max_edge_count"])

        if "created_after" in mapping:
            conditions.append("created_at >= ?")
            params.append(mapping["created_after"])

        if "created_before" in mapping:
            conditions.append("created_at <= ?")
            params.append(mapping["created_before"])

        if "updated_after" in mapping:
            conditions.append("updated_at >= ?")
            params.append(mapping["updated_after"])

        if "updated_before" in mapping:
            conditions.append("updated_at <= ?")
            params.append(mapping["updated_before"])

        return conditions, params

    def _build_order_clause(self, sort: Optional[SortParams]) -> str:
        """Build ORDER BY clause from sort parameters."""

        sort_info = self._resolve_sort(sort)
        db_field = sort_info["field"]
        direction = "ASC" if sort_info["direction"] == SortDirection.ASC else "DESC"
        return f"ORDER BY {db_field} {direction}"

    def _row_to_knowledge_graph(self, row) -> KnowledgeGraph:
        """Convert database row to ``KnowledgeGraph`` entity."""

        data = {
            "id": row[0],
            "name": row[1],
            "tenant_id": row[2],
            "domain": row[3],
            "ontology_version_id": row[4],
            "created_at": row[5],
            "updated_at": row[6],
            "node_count": row[7],
            "edge_count": row[8],
            "is_public": row[9],
        }
        if isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if not isinstance(data["is_public"], bool):
            data["is_public"] = bool(data["is_public"])

        return self._dict_to_entity(data)


DatabaseKnowledgeGraphRepository = RawSQLKnowledgeGraphRepository
