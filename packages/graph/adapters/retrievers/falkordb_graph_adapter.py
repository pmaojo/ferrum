"""FalkorDB graph adapter with Lua script optimization for performance.

This adapter implements connection management with pre-loaded Lua scripts,
bulk insert functionality with Redis Streams back-pressure, optimistic locking
with tenant isolation, and ontology version storage for delta validation.
"""

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from domain.entities import KnowledgeGraph, OntologyVersion, Triple

from .falkordb_connection_manager import FalkorDBConnectionManager

# Configure logging
logger = logging.getLogger(__name__)


class FalkorDBException(Exception):
    """Base exception for FalkorDB operations."""

    def __init__(self, message: str, error_code: str, context: Dict[str, Any]):
        self.message = message
        self.error_code = error_code
        self.context = context
        super().__init__(message)


@dataclass
class FalkorDBConfig:
    """Configuration for connecting to FalkorDB."""

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    username: Optional[str] = None
    password: Optional[str] = None
    ssl: bool = False

    def to_url(self) -> str:
        """Build a redis URL from the configuration."""
        credentials = ""
        if self.username or self.password:
            user = self.username or ""
            pwd = self.password or ""
            credentials = f"{user}:{pwd}@"
        protocol = "rediss" if self.ssl else "redis"
        return f"{protocol}://{credentials}{self.host}:{self.port}/{self.db}"


class FalkorGraphAdapter:
    """Adapter for FalkorDB graph database with performance optimizations.

    Implements connection management with pre-loaded Lua scripts (SCRIPT LOAD + EVALSHA),
    bulk insert functionality with Redis Streams back-pressure, optimistic locking
    with tenant isolation, and ontology version storage for delta validation.
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        *,
        connection_config: Optional[FalkorDBConfig] = None,
        scripts_path: Optional[str] = None,
        connection_manager: Optional[FalkorDBConnectionManager] = None,
        max_retries: int = 3,
        batch_size: int = 1000,
        stream_buffer_size: int = 10000,
        cache_ttl: int = 3600,
        stream_key: str = "bulk_insert_stream",
        pool_size: int = 20,
    ):
        """Initialize FalkorGraphAdapter with connection and configuration.

        Args:
            connection_string: FalkorDB connection string
            connection_config: Optional configuration object for connection
            scripts_path: Optional path to Lua scripts directory
            max_retries: Maximum number of retry attempts for operations
            batch_size: Default batch size for bulk operations
            stream_buffer_size: Maximum buffer size for Redis Streams
            cache_ttl: TTL for cached query results in seconds
            stream_key: Redis Stream key used for back-pressure control
            pool_size: Size of the Redis connection pool

        Raises:
            FalkorDBException: When connection fails or scripts cannot be loaded
        """
        if connection_manager is not None:
            self.connection_manager = connection_manager
        else:
            if connection_config is not None:
                self.connection_string = connection_config.to_url()
            elif connection_string is not None:
                self.connection_string = connection_string
            else:
                raise ValueError(
                    "Either connection_string or connection_config must be provided"
                )
            self.connection_manager = FalkorDBConnectionManager(
                self.connection_string,
                pool_size=pool_size,
                scripts_path=None,
            )
        self.scripts_path = (
            Path(scripts_path)
            if scripts_path
            else Path(__file__).parent.parent / "lua_scripts"
        )
        self.max_retries = max_retries
        self.batch_size = batch_size
        self.stream_buffer_size = stream_buffer_size
        self.cache_ttl = cache_ttl
        self.stream_key = stream_key
        self.pool_size = pool_size

        self.client = self.connection_manager.client

        # Load Lua scripts for performance optimization with retry
        self.connection_manager.load_lua_scripts_with_retry(self.scripts_path)

    def execute_cypher_batch(
        self, queries: List[str], graph_name: str = "knowledge_graph"
    ) -> List[Any]:
        """Execute multiple Cypher queries in a batch for better performance."""
        results = []
        pipe = self.client.pipeline()

        try:
            for query in queries:
                pipe.graph(graph_name).query(query)

            batch_results = pipe.execute()

            for result in batch_results:
                if hasattr(result, "result_set"):
                    results.append(
                        [
                            {result.header[i]: row[i] for i in range(len(row))}
                            for row in result.result_set
                        ]
                    )
                else:
                    results.append(result)

            return results

        except Exception as e:
            logger.error(f"FalkorDB batch execution error: {e}")
            raise RuntimeError(f"Batch query execution failed: {e}")

    def create_graph_index(
        self,
        graph_name: str,
        node_label: str,
        property_name: str,
        index_type: str = "BTREE",
    ) -> bool:
        """Create optimized indexes for better query performance."""
        try:
            query = f"CREATE INDEX FOR (n:{node_label}) ON (n.{property_name})"
            self.client.graph(graph_name).query(query)
            logger.info(f"Created index on {node_label}.{property_name}")
            return True
        except Exception as e:
            logger.error(f"Index creation failed: {e}")
            return False

    async def get_graph_metrics(self, graph_name: str) -> Dict[str, Any]:
        """Get comprehensive graph metrics and statistics."""
        queries = [
            "MATCH (n) RETURN count(n) as node_count",
            "MATCH ()-[r]->() RETURN count(r) as relationship_count",
            "MATCH (n) RETURN labels(n)[0] as label, count(*) as count",
            "MATCH ()-[r]->() RETURN type(r) as rel_type, count(*) as count",
        ]

        try:
            results = self.execute_cypher_batch(queries, graph_name)

            return {
                "node_count": results[0][0]["node_count"] if results[0] else 0,
                "relationship_count": (
                    results[1][0]["relationship_count"] if results[1] else 0
                ),
                "node_types": (
                    {r["label"]: r["count"] for r in results[2]} if results[2] else {}
                ),
                "relationship_types": (
                    {r["rel_type"]: r["count"] for r in results[3]}
                    if results[3]
                    else {}
                ),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Graph metrics error: {e}")
            return {"error": str(e)}

    async def find_communities(
        self, graph_name: str, algorithm: str = "louvain", min_community_size: int = 3
    ) -> Dict[str, Any]:
        """Advanced community detection with multiple algorithms."""
        try:
            if algorithm == "louvain":
                query = f"""
                CALL gds.louvain.stream({{
                    nodeProjection: '*',
                    relationshipProjection: '*'
                }})
                YIELD nodeId, communityId
                WITH communityId, collect(nodeId) as members
                WHERE size(members) >= {min_community_size}
                RETURN communityId, members, size(members) as size
                ORDER BY size DESC
                """
            else:
                # Fallback to basic connected components
                query = """
                MATCH (n)
                CALL apoc.path.expandConfig(n, {relationshipFilter: '', labelFilter: '', uniqueness: 'NODE_GLOBAL'})
                YIELD path
                WITH collect(distinct nodes(path)) as component
                WHERE size(component) >= $min_size
                RETURN component
                """

            result = self.client.graph(graph_name).query(query)
            communities = []

            if hasattr(result, "result_set"):
                for row in result.result_set:
                    communities.append(
                        {"id": row[0], "members": row[1], "size": row[2]}
                    )

            return {
                "algorithm": algorithm,
                "communities": communities,
                "total_communities": len(communities),
            }

        except Exception as e:
            logger.error(f"Community detection error: {e}")
            return {"error": str(e)}

    def bulk_insert(
        self,
        *,
        triples: List[Triple],
        kg_id: str,
        tenant_id: str,
        batch_size: Optional[int] = None,
    ) -> int:
        """Insert triples in bulk using Lua script optimization.

        Uses pre-loaded Lua scripts with EVALSHA for atomic operations,
        Redis Streams back-pressure with batcher tokens, and optimistic
        locking with tenant isolation to avoid watch/unwatch CPU hunger.

        Args:
            triples: List of Triple objects to insert
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            batch_size: Optional custom batch size (defaults to self.batch_size)

        Returns:
            Number of triples successfully inserted

        Raises:
            FalkorDBException: When bulk insert fails
        """
        if not triples:
            logger.warning(f"No triples provided for bulk insert to kg_id={kg_id}")
            return 0

        logger.info(
            f"Bulk inserting {len(triples)} triples to kg_id={kg_id}, tenant_id={tenant_id}"
        )

        # Use provided batch size or default
        effective_batch_size = batch_size or self.batch_size

        try:
            # Split triples into batches for processing
            batches = self._split_into_batches(triples, effective_batch_size)
            total_inserted = 0

            # Process each batch with back-pressure control
            for i, batch in enumerate(batches):
                logger.debug(
                    f"Processing batch {i+1}/{len(batches)} with {len(batch)} triples"
                )

                # Apply back-pressure control using Redis Streams
                self._apply_back_pressure()

                # Convert triples to serializable format for Lua script
                serialized_batch = self._serialize_triples(batch)

                # Execute bulk insert Lua script with EVALSHA
                result = self._execute_lua_script(
                    script_name="bulk_insert",
                    keys=[kg_id, tenant_id],
                    args=[json.dumps(serialized_batch)],
                )

                # Parse result and update total
                batch_result = json.loads(result) if isinstance(result, str) else result
                batch_inserted = batch_result.get("inserted", 0)
                total_inserted += batch_inserted

                logger.debug(f"Batch {i+1} inserted {batch_inserted} triples")

                # Update knowledge graph metadata
                self._update_kg_metadata(kg_id, tenant_id, batch_inserted, 0)

            logger.info(f"Successfully inserted {total_inserted} triples")
            return total_inserted

        except Exception as e:
            logger.error(f"Bulk insert failed: {str(e)}", exc_info=True)
            raise FalkorDBException(
                message=f"Bulk insert failed: {str(e)}",
                error_code="FALKORDB_BULK_INSERT_ERROR",
                context={
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "triple_count": len(triples),
                },
            ) from e

    def query(
        self,
        *,
        cypher: str,
        kg_id: str,
        tenant_id: str,
        params: Optional[Dict[str, Any]] = None,
        timeout_ms: int = 30000,
        enable_optimization: bool = True,
        collect_metrics: bool = True,
    ) -> Dict[str, Any]:
        """Execute Cypher query with tenant filtering and performance monitoring.

        Executes graph queries with automatic tenant isolation, query optimization,
        and comprehensive performance metrics collection.

        Args:
            cypher: Cypher query string
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            params: Optional query parameters
            timeout_ms: Query timeout in milliseconds
            enable_optimization: Whether to enable query optimization
            collect_metrics: Whether to collect detailed performance metrics

        Returns:
            Dictionary containing query results and performance metrics:
            {
                "results": List[Dict[str, Any]],
                "execution_time_ms": float,
                "metrics": Dict[str, Any],
                "result_count": int,
                "query_plan": Optional[Dict[str, Any]]
            }

        Raises:
            FalkorDBException: When query execution fails
        """
        logger.info(
            f"Executing Cypher query for kg_id={kg_id}, tenant_id={tenant_id}, "
            f"optimization={enable_optimization}, metrics={collect_metrics}"
        )

        start_time = datetime.now()
        query_hash = hashlib.md5(cypher.encode()).hexdigest()[:8]

        try:
            # Prepare query parameters with optimization flags
            query_params = params or {}
            query_params.update(
                {
                    "tenant_id": tenant_id,
                    "kg_id": kg_id,
                    "enable_optimization": enable_optimization,
                    "collect_metrics": collect_metrics,
                    "query_hash": query_hash,
                }
            )

            # Check query cache if optimization is enabled
            cached_result = None
            if enable_optimization:
                cached_result = self._check_query_cache(
                    kg_id=kg_id,
                    tenant_id=tenant_id,
                    query_hash=query_hash,
                    params=query_params,
                )

            if cached_result:
                logger.debug(f"Query cache hit for query_hash={query_hash}")
                return cached_result

            # Execute tenant-filtered query using Lua script
            result = self._execute_lua_script(
                script_name="tenant_filtered_query",
                keys=[kg_id, tenant_id],
                args=[cypher, json.dumps(query_params), str(timeout_ms)],
            )

            # Parse result from Lua script
            query_result = json.loads(result) if isinstance(result, str) else result

            # Handle errors from Lua script
            if "error" in query_result:
                raise FalkorDBException(
                    message=query_result["error"],
                    error_code="FALKORDB_QUERY_EXECUTION_ERROR",
                    context={
                        "kg_id": kg_id,
                        "tenant_id": tenant_id,
                        "query_hash": query_hash,
                    },
                )

            # Calculate total execution time
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Enhance result with additional metrics
            enhanced_result = {
                "results": query_result.get("results", []),
                "execution_time_ms": execution_time_ms,
                "metrics": query_result.get("metrics", {}),
                "result_count": query_result.get("result_count", 0),
                "query_plan": None,  # Would be populated by actual query planner
            }

            # Add performance metrics (always add basic metrics)
            enhanced_result["metrics"].update(
                {
                    "total_execution_time_ms": execution_time_ms,
                    "lua_execution_time_ms": query_result.get("execution_time_ms", 0),
                    "overhead_ms": execution_time_ms
                    - query_result.get("execution_time_ms", 0),
                    "query_hash": query_hash,
                    "cache_hit": False,
                    "optimization_enabled": enable_optimization,
                }
            )

            # Add detailed metrics if collection is enabled
            if collect_metrics:
                enhanced_result["metrics"].update({"detailed_metrics_collected": True})

            # Cache result if optimization is enabled and query is cacheable
            if enable_optimization and self._is_query_cacheable(
                cypher, enhanced_result
            ):
                self._cache_query_result(
                    kg_id=kg_id,
                    tenant_id=tenant_id,
                    query_hash=query_hash,
                    params=query_params,
                    result=enhanced_result,
                )

            # Record performance metrics for monitoring
            if collect_metrics:
                self._record_query_metrics(
                    kg_id=kg_id,
                    tenant_id=tenant_id,
                    execution_time_ms=execution_time_ms,
                    result_count=enhanced_result["result_count"],
                    metrics=enhanced_result["metrics"],
                )

            # Log performance information
            logger.debug(
                f"Query execution completed in {execution_time_ms:.2f}ms with "
                f"{enhanced_result['result_count']} results"
            )

            # Log slow queries for optimization
            if execution_time_ms > 1000:  # Slow query threshold
                logger.warning(
                    f"Slow query detected: {execution_time_ms:.2f}ms for query_hash={query_hash}, "
                    f"kg_id={kg_id}, tenant_id={tenant_id}"
                )

            return enhanced_result

        except FalkorDBException:
            # Re-raise FalkorDB exceptions
            raise
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}", exc_info=True)
            raise FalkorDBException(
                message=f"Query execution failed: {str(e)}",
                error_code="FALKORDB_QUERY_ERROR",
                context={
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "cypher": cypher[:100] + ("..." if len(cypher) > 100 else ""),
                    "query_hash": query_hash,
                },
            ) from e

    def store_ontology_version(self, *, version: OntologyVersion) -> bool:
        """Store ontology version as a node in FalkorDB for delta validation.

        Stores ontology versions as :Ontology {version} nodes in FalkorDB
        to enable delta validation and version tracking for ontologies.

        Args:
            version: OntologyVersion entity to store

        Returns:
            True if version was stored successfully, False otherwise

        Raises:
            FalkorDBException: When version storage fails
        """
        logger.info(
            f"Storing ontology version {version.id} for tenant {version.tenant_id}"
        )

        try:
            # Serialize ontology version for Lua script
            serialized_version = {
                "id": version.id,
                "checksum": version.checksum,
                "parent_version": version.parent_version,
                "tenant_id": version.tenant_id,
                "created_at": version.created_at.isoformat(),
                "axiom_count": len(version.axioms),
                "axioms": version.axioms,
            }

            # Execute store ontology version Lua script
            result = self._execute_lua_script(
                script_name="store_ontology_version",
                keys=[version.id, version.tenant_id],
                args=[json.dumps(serialized_version)],
            )

            # Parse result
            storage_result = json.loads(result) if isinstance(result, str) else result
            success = storage_result.get("success", False)

            if success:
                logger.info(f"Successfully stored ontology version {version.id}")
            else:
                logger.warning(
                    f"Failed to store ontology version {version.id}: "
                    f"{storage_result.get('error', 'Unknown error')}"
                )

            return success

        except Exception as e:
            logger.error(f"Ontology version storage failed: {str(e)}", exc_info=True)
            raise FalkorDBException(
                message=f"Ontology version storage failed: {str(e)}",
                error_code="FALKORDB_ONTOLOGY_STORAGE_ERROR",
                context={"version_id": version.id, "tenant_id": version.tenant_id},
            ) from e

    def get_ontology_version(
        self, *, version_id: str, tenant_id: str
    ) -> Optional[OntologyVersion]:
        """Retrieve ontology version from FalkorDB.

        Retrieves ontology version stored as :Ontology {version} node
        in FalkorDB for delta validation and version tracking.

        Args:
            version_id: Ontology version identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            OntologyVersion entity if found, None otherwise

        Raises:
            FalkorDBException: When version retrieval fails
        """
        logger.info(f"Retrieving ontology version {version_id} for tenant {tenant_id}")

        try:
            # Execute Cypher query to retrieve ontology version
            cypher = """
            MATCH (o:Ontology {id: $version_id, tenant_id: $tenant_id})
            RETURN o
            """

            params = {"version_id": version_id, "tenant_id": tenant_id}

            result = self.query(
                cypher=cypher,
                kg_id="ontology_store",  # Special graph for ontology storage
                tenant_id=tenant_id,
                params=params,
            )

            if not result:
                logger.info(f"Ontology version {version_id} not found")
                return None

            # Parse ontology version from result
            ontology_data = result[0].get("o", {})

            # Create OntologyVersion entity
            version = OntologyVersion(
                id=ontology_data.get("id", version_id),
                checksum=ontology_data.get("checksum", ""),
                parent_version=ontology_data.get("parent_version"),
                tenant_id=ontology_data.get("tenant_id", tenant_id),
                created_at=datetime.fromisoformat(
                    ontology_data.get("created_at", datetime.now().isoformat())
                ),
                axioms=ontology_data.get("axioms", []),
            )

            logger.info(
                f"Retrieved ontology version {version_id} with {len(version.axioms)} axioms"
            )
            return version

        except Exception as e:
            logger.error(f"Ontology version retrieval failed: {str(e)}", exc_info=True)
            raise FalkorDBException(
                message=f"Ontology version retrieval failed: {str(e)}",
                error_code="FALKORDB_ONTOLOGY_RETRIEVAL_ERROR",
                context={"version_id": version_id, "tenant_id": tenant_id},
            ) from e

    def create_knowledge_graph(
        self, *, name: str, tenant_id: str, ontology_version_id: Optional[str] = None
    ) -> KnowledgeGraph:
        """Create a new knowledge graph with tenant isolation.

        Creates a new knowledge graph with tenant isolation and
        optional ontology version for validation.

        Args:
            name: Knowledge graph name
            tenant_id: Tenant identifier for multi-tenant isolation
            ontology_version_id: Optional ontology version for validation

        Returns:
            Created KnowledgeGraph entity

        Raises:
            FalkorDBException: When knowledge graph creation fails
        """
        logger.info(f"Creating knowledge graph '{name}' for tenant {tenant_id}")

        try:
            # Generate knowledge graph ID
            kg_id = f"kg_{uuid.uuid4().hex[:8]}_{int(time.time())}"

            # Create knowledge graph entity
            kg = KnowledgeGraph(
                id=kg_id,
                name=name,
                tenant_id=tenant_id,
                ontology_version_id=ontology_version_id or "",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                node_count=0,
                edge_count=0,
            )

            # Execute Cypher query to create knowledge graph
            cypher = """
            CREATE (kg:KnowledgeGraph {
                id: $id,
                name: $name,
                tenant_id: $tenant_id,
                ontology_version_id: $ontology_version_id,
                created_at: $created_at,
                updated_at: $updated_at,
                node_count: $node_count,
                edge_count: $edge_count
            })
            RETURN kg
            """

            params = {
                "id": kg.id,
                "name": kg.name,
                "tenant_id": kg.tenant_id,
                "ontology_version_id": kg.ontology_version_id,
                "created_at": kg.created_at.isoformat(),
                "updated_at": kg.updated_at.isoformat(),
                "node_count": kg.node_count,
                "edge_count": kg.edge_count,
            }

            result = self.query(
                cypher=cypher,
                kg_id="kg_metadata",  # Special graph for metadata
                tenant_id=tenant_id,
                params=params,
            )

            logger.info(f"Created knowledge graph {kg_id}")
            return kg

        except Exception as e:
            logger.error(f"Knowledge graph creation failed: {str(e)}", exc_info=True)
            raise FalkorDBException(
                message=f"Knowledge graph creation failed: {str(e)}",
                error_code="FALKORDB_KG_CREATION_ERROR",
                context={"name": name, "tenant_id": tenant_id},
            ) from e

    def get_knowledge_graph(
        self, *, kg_id: str, tenant_id: str
    ) -> Optional[KnowledgeGraph]:
        """Retrieve knowledge graph metadata.

        Retrieves knowledge graph metadata including node and edge counts,
        ontology version, and creation/update timestamps.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            KnowledgeGraph entity if found, None otherwise

        Raises:
            FalkorDBException: When knowledge graph retrieval fails
        """
        logger.info(f"Retrieving knowledge graph {kg_id} for tenant {tenant_id}")

        try:
            # Execute Cypher query to retrieve knowledge graph
            cypher = """
            MATCH (kg:KnowledgeGraph {id: $kg_id, tenant_id: $tenant_id})
            RETURN kg
            """

            params = {"kg_id": kg_id, "tenant_id": tenant_id}

            result = self.query(
                cypher=cypher,
                kg_id="kg_metadata",  # Special graph for metadata
                tenant_id=tenant_id,
                params=params,
            )

            if not result:
                logger.info(f"Knowledge graph {kg_id} not found")
                return None

            # Parse knowledge graph from result
            kg_data = result[0].get("kg", {})

            # Create KnowledgeGraph entity
            kg = KnowledgeGraph(
                id=kg_data.get("id", kg_id),
                name=kg_data.get("name", ""),
                tenant_id=kg_data.get("tenant_id", tenant_id),
                ontology_version_id=kg_data.get("ontology_version_id", ""),
                created_at=datetime.fromisoformat(
                    kg_data.get("created_at", datetime.now().isoformat())
                ),
                updated_at=datetime.fromisoformat(
                    kg_data.get("updated_at", datetime.now().isoformat())
                ),
                node_count=kg_data.get("node_count", 0),
                edge_count=kg_data.get("edge_count", 0),
            )

            logger.info(
                f"Retrieved knowledge graph {kg_id} with {kg.node_count} nodes "
                f"and {kg.edge_count} edges"
            )
            return kg

        except Exception as e:
            logger.error(f"Knowledge graph retrieval failed: {str(e)}", exc_info=True)
            raise FalkorDBException(
                message=f"Knowledge graph retrieval failed: {str(e)}",
                error_code="FALKORDB_KG_RETRIEVAL_ERROR",
                context={"kg_id": kg_id, "tenant_id": tenant_id},
            ) from e

    def _execute_lua_script(
        self, *, script_name: str, keys: List[str], args: List[Any]
    ) -> Any:
        """Execute Lua script using EVALSHA for atomic operations.

        Args:
            script_name: Name of the pre-loaded Lua script
            keys: Redis keys for EVALSHA
            args: Arguments for EVALSHA

        Returns:
            Script execution result

        Raises:
            FalkorDBException: When script execution fails
        """
        if script_name not in self.connection_manager.scripts:
            available_scripts = list(self.connection_manager.scripts.keys())
            logger.warning(
                f"Lua script '{script_name}' not loaded. Available scripts: {available_scripts}"
            )
            logger.info("Attempting to reload Lua scripts...")

            try:
                # Try to reload scripts
                self.connection_manager.load_lua_scripts(self.scripts_path)
                if script_name in self.connection_manager.scripts:
                    logger.info(f"Successfully reloaded script '{script_name}'")
                else:
                    raise FalkorDBException(
                        message=f"Lua script '{script_name}' still not available after reload. Available scripts: {list(self.connection_manager.scripts.keys())}",
                        error_code="FALKORDB_SCRIPT_NOT_FOUND",
                        context={
                            "script_name": script_name,
                            "available_scripts": list(
                                self.connection_manager.scripts.keys()
                            ),
                            "scripts_path": str(self.scripts_path),
                        },
                    )
            except Exception as reload_error:
                logger.error(f"Failed to reload Lua scripts: {str(reload_error)}")
                raise FalkorDBException(
                    message=f"Lua script '{script_name}' not loaded and reload failed: {str(reload_error)}",
                    error_code="FALKORDB_SCRIPT_NOT_FOUND",
                    context={
                        "script_name": script_name,
                        "available_scripts": available_scripts,
                        "scripts_path": str(self.scripts_path),
                        "reload_error": str(reload_error),
                    },
                ) from reload_error

        script_sha = self.connection_manager.scripts[script_name]

        try:
            return self.client.evalsha(script_sha, len(keys), *(keys + args))
        except Exception as e:
            if "NOSCRIPT" in str(e):
                # Reload missing script and retry once
                script_body = self.connection_manager.script_sources.get(script_name)
                if script_body is None:
                    raise FalkorDBException(
                        message=f"Lua script body for '{script_name}' not found",
                        error_code="FALKORDB_SCRIPT_NOT_FOUND",
                        context={"script_name": script_name},
                    ) from e
                script_sha = self.connection_manager.reload_script(script_name)
                return self.client.evalsha(script_sha, len(keys), *(keys + args))
            else:
                logger.error(
                    f"Failed to execute Lua script '{script_name}': {str(e)}",
                    exc_info=True,
                )
                raise FalkorDBException(
                    message=f"Failed to execute Lua script '{script_name}': {str(e)}",
                    error_code="FALKORDB_SCRIPT_EXECUTION_ERROR",
                    context={"script_name": script_name, "keys": keys},
                ) from e

    def _split_into_batches(
        self, triples: List[Triple], batch_size: int
    ) -> List[List[Triple]]:
        """Split triples into batches for bulk processing.

        Args:
            triples: List of Triple objects
            batch_size: Maximum batch size

        Returns:
            List of triple batches
        """
        return [triples[i : i + batch_size] for i in range(0, len(triples), batch_size)]

    def _serialize_triples(self, triples: List[Triple]) -> List[Dict[str, str]]:
        """Serialize Triple objects for Lua script execution.

        Args:
            triples: List of Triple objects

        Returns:
            List of serialized triples as dictionaries
        """
        return [
            {
                "subject": triple.subject,
                "predicate": triple.predicate,
                "object": triple.object,
                "tenant_id": triple.tenant_id,
            }
            for triple in triples
        ]

    def _apply_back_pressure(self) -> None:
        """Apply back-pressure control using Redis Streams."""

        try:
            while self.client.xlen(self.stream_key) >= self.stream_buffer_size:
                logger.debug("Waiting for stream buffer to free up")
                time.sleep(0.05)
        except Exception as e:
            logger.warning(f"Back-pressure management failed: {str(e)}")

        try:
            self.client.xadd(
                self.stream_key,
                {"seq": str(uuid.uuid4())},
                maxlen=self.stream_buffer_size,
                approximate=True,
            )
        except Exception as e:
            logger.warning(f"Failed to record batch in stream: {str(e)}")

    def _update_kg_metadata(
        self, kg_id: str, tenant_id: str, nodes_added: int, edges_added: int
    ) -> None:
        """Update knowledge graph metadata with optimistic locking.

        Uses optimistic locking with tenant isolation to update
        knowledge graph metadata without watch/unwatch CPU hunger.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier
            nodes_added: Number of nodes added
            edges_added: Number of edges added
        """
        if nodes_added == 0 and edges_added == 0:
            return

        try:
            self._execute_lua_script(
                script_name="optimistic_update",
                keys=[f"kg:{kg_id}:{tenant_id}"],
                args=[str(nodes_added), str(edges_added), datetime.now().isoformat()],
            )

            logger.debug(
                f"Updated knowledge graph {kg_id} metadata: +{nodes_added} nodes, +{edges_added} edges"
            )

            self._invalidate_query_cache(kg_id, tenant_id)

        except Exception as e:
            logger.warning(
                f"Failed to update knowledge graph metadata: {str(e)}", exc_info=True
            )

    def _check_query_cache(
        self, *, kg_id: str, tenant_id: str, query_hash: str, params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if query result is cached and still valid.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier
            query_hash: MD5 hash of the query
            params: Query parameters

        Returns:
            Cached result if found and valid, None otherwise
        """
        try:
            cache_key = f"cache:query:{kg_id}:{tenant_id}:{query_hash}"
            cached = self.client.get(cache_key)
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            logger.warning(f"Query cache check failed: {str(e)}")
            return None

    def _cache_query_result(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        query_hash: str,
        params: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        """Cache query result for future use.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier
            query_hash: MD5 hash of the query
            params: Query parameters
        """
        try:
            cache_key = f"cache:query:{kg_id}:{tenant_id}:{query_hash}"
            index_key = f"cache:index:{kg_id}:{tenant_id}"
            pipeline = self.client.pipeline()
            pipeline.set(cache_key, json.dumps(result), ex=self.cache_ttl)
            pipeline.sadd(index_key, cache_key)
            pipeline.execute()
            logger.debug(f"Caching query result for query_hash={query_hash}")
        except Exception as e:
            logger.warning(f"Query result caching failed: {str(e)}")

    def _invalidate_query_cache(self, kg_id: str, tenant_id: str) -> None:
        """Invalidate cached query results for a knowledge graph."""
        index_key = f"cache:index:{kg_id}:{tenant_id}"
        try:
            keys = self.client.smembers(index_key)
            if keys:
                pipeline = self.client.pipeline()
                for key in keys:
                    pipeline.delete(key)
                pipeline.delete(index_key)
                pipeline.execute()
        except Exception as e:
            logger.warning(f"Failed to invalidate query cache: {str(e)}")

    def _is_query_cacheable(self, cypher: str, result: Dict[str, Any]) -> bool:
        """Determine if a query result should be cached.

        Args:
            cypher: Cypher query string
            result: Query result

        Returns:
            True if query should be cached, False otherwise
        """
        # Don't cache queries with mutations
        if any(
            keyword in cypher.upper()
            for keyword in ["CREATE", "DELETE", "SET", "REMOVE", "MERGE"]
        ):
            return False

        # Don't cache queries that took too long (likely one-time complex queries)
        if result.get("execution_time_ms", 0) > 5000:
            return False

        # Don't cache queries with too many results (memory concerns)
        if result.get("result_count", 0) > 1000:
            return False

        # Cache read-only queries with reasonable size and execution time
        return True

    def _record_query_metrics(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        execution_time_ms: float,
        result_count: int,
        metrics: Dict[str, Any],
    ) -> None:
        """Record query performance metrics for monitoring.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier
            execution_time_ms: Query execution time in milliseconds
            result_count: Number of results returned
            metrics: Additional metrics from query execution
        """
        try:
            # In a real implementation, we would:
            # 1. Send metrics to OpenTelemetry/Prometheus
            # 2. Update performance dashboards
            # 3. Trigger alerts for performance degradation

            # Record key performance indicators
            # Log metrics for monitoring systems
            logger.info(
                f"Query metrics recorded for kg_id={kg_id}, tenant_id={tenant_id}: "
                f"latency={execution_time_ms:.2f}ms, results={result_count}, "
                f"nodes_scanned={metrics.get('nodes_scanned', 0)}, "
                f"edges_scanned={metrics.get('edges_scanned', 0)}"
            )

            # Check for performance degradation
            if execution_time_ms > 1000:  # p95 threshold
                logger.warning(
                    f"Query performance degradation detected: {execution_time_ms:.2f}ms "
                    f"exceeds p95 threshold for kg_id={kg_id}, tenant_id={tenant_id}"
                )

        except Exception as e:
            logger.warning(f"Failed to record query metrics: {str(e)}")

    def get_query_statistics(
        self, *, kg_id: str, tenant_id: str, time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """Get query performance statistics for a knowledge graph.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier
            time_range_hours: Time range for statistics in hours

        Returns:
            Dictionary containing query performance statistics
        """
        logger.info(
            f"Retrieving query statistics for kg_id={kg_id}, tenant_id={tenant_id}, "
            f"time_range={time_range_hours}h"
        )

        try:
            # Execute Cypher query to get statistics
            cypher = """
            MATCH (s:QueryStats {kg_id: $kg_id, tenant_id: $tenant_id})
            WHERE s.timestamp > datetime() - duration({hours: $time_range_hours})
            RETURN
                count(s) as query_count,
                avg(s.execution_time_ms) as avg_latency_ms,
                percentileCont(s.execution_time_ms, 0.95) as p95_latency_ms,
                sum(s.result_count) as total_results,
                sum(CASE WHEN s.execution_time_ms > 1000 THEN 1 ELSE 0 END) as slow_query_count
            """

            params = {
                "kg_id": kg_id,
                "tenant_id": tenant_id,
                "time_range_hours": time_range_hours,
            }

            result = self.query(
                cypher=cypher,
                kg_id="query_stats",  # Special graph for statistics
                tenant_id=tenant_id,
                params=params,
                collect_metrics=False,  # Avoid recursive metrics collection
            )

            if result.get("results"):
                stats_data = result["results"][0]
                return {
                    "query_count": stats_data.get("query_count", 0),
                    "avg_latency_ms": stats_data.get("avg_latency_ms", 0.0),
                    "p95_latency_ms": stats_data.get("p95_latency_ms", 0.0),
                    "total_results": stats_data.get("total_results", 0),
                    "slow_query_count": stats_data.get("slow_query_count", 0),
                    "slow_query_ratio": (
                        stats_data.get("slow_query_count", 0)
                        / max(stats_data.get("query_count", 1), 1)
                    ),
                    "time_range_hours": time_range_hours,
                }
            else:
                return {
                    "query_count": 0,
                    "avg_latency_ms": 0.0,
                    "p95_latency_ms": 0.0,
                    "total_results": 0,
                    "slow_query_count": 0,
                    "slow_query_ratio": 0.0,
                    "time_range_hours": time_range_hours,
                }

        except Exception as e:
            logger.error(
                f"Failed to retrieve query statistics: {str(e)}", exc_info=True
            )
            raise FalkorDBException(
                message=f"Failed to retrieve query statistics: {str(e)}",
                error_code="FALKORDB_STATS_ERROR",
                context={
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "time_range_hours": time_range_hours,
                },
            ) from e

    def optimize_query(
        self, *, cypher: str, kg_id: str, tenant_id: str
    ) -> Dict[str, Any]:
        """Analyze and optimize a Cypher query for better performance.

        Args:
            cypher: Cypher query string to optimize
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Returns:
            Dictionary containing optimization suggestions and analysis
        """
        logger.info(
            f"Analyzing query optimization for kg_id={kg_id}, tenant_id={tenant_id}"
        )

        try:
            optimization_suggestions = []
            query_analysis = {
                "original_query": cypher,
                "complexity_score": 0,
                "estimated_cost": 0,
                "index_usage": [],
                "bottlenecks": [],
            }

            query_lower = cypher.lower()

            # Analyze query patterns and suggest optimizations

            # Check for missing WHERE clauses
            if "match" in query_lower and "where" not in query_lower:
                optimization_suggestions.append(
                    {
                        "type": "missing_filter",
                        "message": "Consider adding WHERE clause to filter results early",
                        "impact": "high",
                    }
                )
                query_analysis["complexity_score"] += 3

            # Check for Cartesian products
            if query_lower.count("match") > 1 and "where" not in query_lower:
                optimization_suggestions.append(
                    {
                        "type": "cartesian_product",
                        "message": "Multiple MATCH clauses without WHERE may cause Cartesian product",
                        "impact": "critical",
                    }
                )
                query_analysis["complexity_score"] += 5

            # Check for implicit Cartesian products (multiple unconnected patterns)
            if (
                "match (a), (b)" in query_lower
                or "match(a),(b)" in query_lower.replace(" ", "")
            ):
                optimization_suggestions.append(
                    {
                        "type": "cartesian_product",
                        "message": "Unconnected patterns in MATCH clause will cause Cartesian product",
                        "impact": "critical",
                    }
                )
                query_analysis["complexity_score"] += 8

            # Check for inefficient patterns
            if "match (n)" in query_lower:
                optimization_suggestions.append(
                    {
                        "type": "full_scan",
                        "message": "Full node scan detected - consider adding labels or properties",
                        "impact": "high",
                    }
                )
                query_analysis["complexity_score"] += 4

            # Check for index opportunities
            if "n.id =" in query_lower or "n.name =" in query_lower:
                query_analysis["index_usage"].append("property_lookup")
                optimization_suggestions.append(
                    {
                        "type": "index_hint",
                        "message": "Property lookup detected - ensure index exists on property",
                        "impact": "medium",
                    }
                )

            # Estimate query cost based on complexity
            query_analysis["estimated_cost"] = min(
                query_analysis["complexity_score"] * 100, 1000
            )

            # Generate optimized query suggestion
            optimized_query = self._generate_optimized_query(
                cypher, optimization_suggestions
            )

            return {
                "analysis": query_analysis,
                "suggestions": optimization_suggestions,
                "optimized_query": optimized_query,
                "optimization_score": max(0, 10 - query_analysis["complexity_score"]),
            }

        except Exception as e:
            logger.error(f"Query optimization analysis failed: {str(e)}", exc_info=True)
            raise FalkorDBException(
                message=f"Query optimization analysis failed: {str(e)}",
                error_code="FALKORDB_OPTIMIZATION_ERROR",
                context={
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "cypher": cypher[:100] + ("..." if len(cypher) > 100 else ""),
                },
            ) from e

    def _generate_optimized_query(
        self, original_query: str, suggestions: List[Dict[str, Any]]
    ) -> str:
        """Generate an optimized version of the query based on suggestions."""
        optimized = original_query

        # Apply basic optimizations
        for suggestion in suggestions:
            if suggestion["type"] == "missing_filter":
                if "WHERE" not in optimized.upper():
                    optimized = optimized.replace(
                        "RETURN",
                        "WHERE n.tenant_id = $tenant_id\nRETURN",
                    )
            elif suggestion["type"] == "full_scan":
                optimized = optimized.replace("MATCH (n)", "MATCH (n:Node)")

        return optimized

    def execute_traversal(
        self,
        *,
        traversal: str,
        kg_id: str,
        tenant_id: str,
        params: Optional[Dict[str, Any]] = None,
        timeout_ms: int = 30000,
    ) -> Dict[str, Any]:
        """Execute graph traversal query with tenant filtering.

        This method executes Gremlin-style traversal queries by converting them
        to equivalent Cypher queries for FalkorDB execution.

        Args:
            traversal: Gremlin traversal string
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            params: Optional traversal parameters
            timeout_ms: Traversal timeout in milliseconds

        Returns:
            Dictionary containing traversal results and performance metrics

        Raises:
            FalkorDBException: When traversal execution fails
        """
        logger.info(
            f"Executing graph traversal for kg_id={kg_id}, tenant_id={tenant_id}"
        )

        try:
            # Convert Gremlin traversal to Cypher query
            cypher_query = self._convert_traversal_to_cypher(traversal, params or {})

            # Execute the converted query
            result = self.query(
                cypher=cypher_query,
                kg_id=kg_id,
                tenant_id=tenant_id,
                params=params,
                timeout_ms=timeout_ms,
                enable_optimization=True,
                collect_metrics=True,
            )

            # Add traversal-specific metadata
            result["traversal_type"] = "gremlin_to_cypher"
            result["original_traversal"] = traversal

            return result

        except Exception as e:
            logger.error(f"Traversal execution failed: {str(e)}", exc_info=True)
            raise FalkorDBException(
                message=f"Traversal execution failed: {str(e)}",
                error_code="FALKORDB_TRAVERSAL_ERROR",
                context={
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "traversal": traversal[:100]
                    + ("..." if len(traversal) > 100 else ""),
                },
            ) from e

    def _convert_traversal_to_cypher(
        self, traversal: str, params: Dict[str, Any]
    ) -> str:
        """Convert Gremlin traversal to equivalent Cypher query.

        Args:
            traversal: Gremlin traversal string
            params: Traversal parameters

        Returns:
            Equivalent Cypher query string
        """
        # Basic traversal patterns to Cypher conversion
        cypher = traversal

        # Convert common Gremlin patterns to Cypher
        if "g.V()" in traversal:
            cypher = cypher.replace("g.V()", "MATCH (n)")

        if ".hasLabel(" in traversal:
            import re

            label_match = re.search(r'\.hasLabel\([\'"]([^\'"]+)[\'"]\)', traversal)
            if label_match:
                label = label_match.group(1)
                cypher = cypher.replace(label_match.group(0), f":{label}")

        if ".has(" in traversal:
            import re

            has_match = re.search(
                r'\.has\([\'"]([^\'"]+)[\'"],\s*[\'"]?([^\'"]+)[\'"]?\)', traversal
            )
            if has_match:
                prop, value = has_match.groups()
                cypher = cypher.replace(
                    has_match.group(0), f" WHERE n.{prop} = '{value}'"
                )

        if ".out(" in traversal or ".in(" in traversal:
            cypher = cypher.replace(".out(", "-[r]->").replace(".in(", "<-[r]-")

        if not cypher.strip().startswith("MATCH"):
            cypher = f"MATCH (n) WHERE n.tenant_id = $tenant_id {cypher}"

        if "RETURN" not in cypher.upper():
            cypher += " RETURN n"

        return cypher
