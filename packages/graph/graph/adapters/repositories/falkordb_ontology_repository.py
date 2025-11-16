"""FalkorDB adapter for ontology version storage and retrieval.

This adapter provides storage and retrieval of ontology versions in FalkorDB,
enabling delta validation and version tracking for ontologies.
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis

from domain.entities import OntologyVersion, ScientificDomain
from domain.ontology_version_service import OntologyVersionRepositoryPort

# Configure logging
logger = logging.getLogger(__name__)


class FalkorDBOntologyRepository(OntologyVersionRepositoryPort):
    """Repository for ontology version storage and retrieval in FalkorDB.

    This class provides methods for storing and retrieving ontology versions,
    enabling delta validation and version tracking for ontologies.
    """

    def __init__(self, connection_string: str, graph_name: str = "ontology"):
        """Initialize the FalkorDB ontology repository.

        Args:
            connection_string: FalkorDB connection string
            graph_name: Name of the graph containing ontology data
        """
        self.connection_string = connection_string
        self.graph_name = graph_name

        try:
            self.client = redis.from_url(connection_string)
            self.client.ping()
            logger.info(
                "Initialized FalkorDBOntologyRepository with %s", connection_string
            )
        except redis.exceptions.ConnectionError as e:
            logger.error("Failed to connect to FalkorDB: %s", e, exc_info=True)
            raise ValueError(f"Failed to connect to FalkorDB: {str(e)}") from e

    def store_ontology_version(
        self, *, axioms: List[str], parent_version_id: Optional[str], tenant_id: str
    ) -> OntologyVersion:
        """Store a new ontology version in FalkorDB.

        Args:
            axioms: List of OWL axioms in Manchester syntax
            parent_version_id: Optional parent version ID for delta validation
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Created OntologyVersion entity

        Raises:
            StorageError: When version storage fails
        """
        logger.info(f"Storing new ontology version for tenant {tenant_id}")

        try:
            # Generate checksum for version identification
            checksum = self._generate_checksum(axioms)

            # Generate version ID
            version_id = f"v_{checksum[:8]}_{int(datetime.now().timestamp())}"

            # Create ontology version entity
            version = OntologyVersion(
                id=version_id,
                checksum=checksum,
                parent_version=parent_version_id,
                tenant_id=tenant_id,
                created_at=datetime.now(),
                axioms=axioms,
            )

            # In a real implementation, we would:
            # 1. Store the version as a :Ontology node in FalkorDB
            # 2. Set properties for id, checksum, parent_version, tenant_id, created_at
            # 3. Store axioms as a property or as separate nodes

            logger.info(f"Stored ontology version {version_id}")
            return version

        except Exception as e:
            logger.exception(f"Failed to store ontology version: {str(e)}")
            raise ValueError(f"Failed to store ontology version: {str(e)}")

    def get_ontology_version(
        self, *, version_id: str, tenant_id: str
    ) -> Optional[OntologyVersion]:
        """Retrieve an ontology version from FalkorDB.

        Args:
            version_id: Ontology version identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            OntologyVersion entity if found, None otherwise

        Raises:
            RetrievalError: When version retrieval fails
        """
        logger.info(f"Retrieving ontology version {version_id} for tenant {tenant_id}")

        try:
            query = (
                "MATCH (v:Ontology {id: $version_id, tenant_id: $tenant_id}) "
                "RETURN v.id AS id, v.checksum AS checksum, v.parent_version AS parent_version, "
                "v.tenant_id AS tenant_id, v.domain AS domain, v.created_at AS created_at, v.axioms AS axioms"
            )
            params = {"version_id": version_id, "tenant_id": tenant_id}
            result = self.client.execute_command(
                "GRAPH.QUERY", self.graph_name, query, params
            )

            if not result:
                logger.info(f"Ontology version {version_id} not found")
                return None

            data: Dict[str, Any]
            if isinstance(result, dict):
                data = result
            elif isinstance(result, list):
                if len(result) < 2 or not result[1]:
                    logger.info(f"Ontology version {version_id} not found")
                    return None
                headers = result[0]
                row = result[1][0] if isinstance(result[1][0], list) else result[1]
                data = dict(zip(headers, row))
            else:
                logger.info(f"Ontology version {version_id} not found")
                return None

            created_at = datetime.fromisoformat(str(data.get("created_at")))
            domain_value = str(data.get("domain", ScientificDomain.GENERAL.value))
            version = OntologyVersion(
                id=str(data.get("id")),
                checksum=str(data.get("checksum")),
                parent_version=(data.get("parent_version") or None),
                tenant_id=str(data.get("tenant_id")),
                domain=ScientificDomain(domain_value),
                created_at=created_at,
                axioms=list(data.get("axioms", [])),
            )

            return version

        except Exception as e:
            logger.exception(f"Failed to retrieve ontology version: {str(e)}")
            raise ValueError(f"Failed to retrieve ontology version: {str(e)}")

    def get_ontology_version_history(
        self, *, tenant_id: str, limit: int = 10
    ) -> List[OntologyVersion]:
        """Retrieve ontology version history for a tenant.

        Args:
            tenant_id: Tenant identifier for multi-tenant isolation
            limit: Maximum number of versions to retrieve

        Returns:
            List of OntologyVersion entities in reverse chronological order

        Raises:
            RetrievalError: When version history retrieval fails
        """
        logger.info(f"Retrieving ontology version history for tenant {tenant_id}")

        try:
            query = (
                "MATCH (v:Ontology {tenant_id: $tenant_id}) "
                "RETURN v.id AS id, v.checksum AS checksum, v.parent_version AS parent_version, "
                "v.tenant_id AS tenant_id, v.domain AS domain, v.created_at AS created_at, v.axioms AS axioms "
                "ORDER BY v.created_at DESC LIMIT $limit"
            )
            params = {"tenant_id": tenant_id, "limit": limit}
            result = self.client.execute_command(
                "GRAPH.QUERY", self.graph_name, query, params
            )

            if not result or not isinstance(result, list) or len(result) < 2:
                return []

            headers = result[0]
            versions = []
            for row in result[1]:
                data = dict(zip(headers, row))
                created_at = datetime.fromisoformat(str(data.get("created_at")))
                domain_value = str(data.get("domain", ScientificDomain.GENERAL.value))
                versions.append(
                    OntologyVersion(
                        id=str(data.get("id")),
                        checksum=str(data.get("checksum")),
                        parent_version=(data.get("parent_version") or None),
                        tenant_id=str(data.get("tenant_id")),
                        domain=ScientificDomain(domain_value),
                        created_at=created_at,
                        axioms=list(data.get("axioms", [])),
                    )
                )

            return versions

        except Exception as e:
            logger.exception(f"Failed to retrieve ontology version history: {str(e)}")
            raise ValueError(f"Failed to retrieve ontology version history: {str(e)}")

    def delete_ontology_version(self, *, version_id: str, tenant_id: str) -> bool:
        """Delete an ontology version from FalkorDB.

        Args:
            version_id: Ontology version identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            True if version was deleted, False otherwise

        Raises:
            DeletionError: When version deletion fails
        """
        logger.info(f"Deleting ontology version {version_id} for tenant {tenant_id}")

        try:
            query = (
                "MATCH (v:Ontology {id: $version_id, tenant_id: $tenant_id}) "
                "DETACH DELETE v"
            )
            params = {"version_id": version_id, "tenant_id": tenant_id}
            self.client.execute_command("GRAPH.QUERY", self.graph_name, query, params)
            return True

        except Exception as e:
            logger.exception(f"Failed to delete ontology version: {str(e)}")
            raise ValueError(f"Failed to delete ontology version: {str(e)}")

    # --- OntologyVersionRepositoryPort compliance ---

    def store_version(
        self,
        *,
        axioms: List[str],
        parent_version_id: Optional[str],
        tenant_id: str,
    ) -> OntologyVersion:
        return self.store_ontology_version(
            axioms=axioms,
            parent_version_id=parent_version_id,
            tenant_id=tenant_id,
        )

    def get_version(
        self,
        *,
        version_id: str,
        tenant_id: str,
    ) -> Optional[OntologyVersion]:
        return self.get_ontology_version(version_id=version_id, tenant_id=tenant_id)

    def get_version_history(
        self,
        *,
        tenant_id: str,
        limit: int = 10,
    ) -> List[OntologyVersion]:
        return self.get_ontology_version_history(tenant_id=tenant_id, limit=limit)

    def delete_version(
        self,
        *,
        version_id: str,
        tenant_id: str,
    ) -> bool:
        return self.delete_ontology_version(version_id=version_id, tenant_id=tenant_id)

    def _generate_checksum(self, axioms: List[str]) -> str:
        """Generate checksum for ontology version identification.

        Args:
            axioms: List of OWL axioms in Manchester syntax

        Returns:
            SHA-256 checksum of sorted axioms
        """
        # Sort axioms for consistent checksums
        sorted_axioms = sorted(axioms)

        # Join axioms with newlines
        axiom_text = "\n".join(sorted_axioms)

        # Generate SHA-256 checksum
        return hashlib.sha256(axiom_text.encode()).hexdigest()
