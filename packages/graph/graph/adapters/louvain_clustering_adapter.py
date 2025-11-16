"""Louvain clustering adapter for large graph visualization.

This adapter implements asynchronous Louvain clustering for graphs >50k nodes,
stores meta-nodes as :Community {centroidEmbedding} in FalkorDB, and provides
progressive loading with community-first, then detail-on-demand visualization.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from adapters.retrievers.falkordb_graph_adapter import FalkorGraphAdapter
from application.ports import ClusteringPort
from domain.entities import Community, Triple

# Configure logging
logger = logging.getLogger(__name__)


class ClusteringException(Exception):
    """Base exception for clustering operations."""

    def __init__(self, message: str, error_code: str, context: Dict[str, Any]):
        self.message = message
        self.error_code = error_code
        self.context = context
        super().__init__(message)


class LouvainClusteringAdapter(ClusteringPort):
    """Adapter for graph clustering using Louvain algorithm.

    Implements asynchronous Louvain clustering for graphs >50k nodes,
    stores meta-nodes as :Community {centroidEmbedding} in FalkorDB,
    and provides progressive loading with community-first, then detail-on-demand.
    """

    # Supported clustering algorithms
    SUPPORTED_ALGORITHMS = {"louvain", "leiden", "infomap"}

    # Default parameters for clustering algorithms
    DEFAULT_PARAMS = {
        "louvain": {
            "resolution": 1.0,
            "randomize": True,
            "weight": None,
            "threshold": 1e-7,
            "max_iterations": 20,
        },
        "leiden": {
            "resolution": 1.0,
            "beta": 0.01,
            "weight": None,
            "max_iterations": 10,
        },
        "infomap": {"directed": False, "weight": None, "num_trials": 10},
    }

    def __init__(
        self,
        falkordb_adapter: FalkorGraphAdapter,
        executor_threads: int = 4,
        cache_ttl_seconds: int = 3600,
        min_community_size: int = 3,
        embedding_dimensions: int = 64,
    ):
        """Initialize LouvainClusteringAdapter with FalkorDB adapter.

        Args:
            falkordb_adapter: FalkorDB adapter for graph operations
            executor_threads: Number of threads for parallel processing
            cache_ttl_seconds: Time-to-live for community cache in seconds
            min_community_size: Minimum number of nodes for a community
            embedding_dimensions: Dimensions for centroid embeddings

        Raises:
            ClusteringException: When initialization fails
        """
        self.falkordb = falkordb_adapter
        self.executor = ThreadPoolExecutor(max_workers=executor_threads)
        self.cache_ttl = cache_ttl_seconds
        self.min_community_size = min_community_size
        self.embedding_dimensions = embedding_dimensions
        self.community_cache = {}  # Cache for computed communities

        # Import optional dependencies lazily to avoid hard requirements
        try:
            # For Louvain clustering
            import community as louvain_community
            import networkx as nx

            self.nx = nx
            self.louvain_community = louvain_community

            # For embedding generation
            from sklearn.decomposition import PCA

            self.pca = PCA

            logger.info("Successfully loaded clustering dependencies")
        except ImportError as e:
            logger.warning(f"Clustering dependencies not available: {str(e)}")
            logger.warning(
                "Install with: pip install networkx python-louvain scikit-learn"
            )
            self.nx = None
            self.louvain_community = None
            self.pca = None

    def compute_communities(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        algorithm: str = "louvain",
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Community]:
        """Compute graph communities for large graph visualization using specified algorithm.

        Applies community detection algorithms (Louvain, etc.) to identify
        graph clusters for progressive rendering and visualization optimization.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            algorithm: Clustering algorithm name (default: "louvain")
            params: Optional algorithm-specific parameters

        Returns:
            List of Community objects representing detected clusters

        Raises:
            ClusteringException: When community computation fails
            ValueError: When algorithm is not supported
        """
        logger.info(
            f"Computing communities for kg_id={kg_id}, tenant_id={tenant_id} "
            f"using {algorithm} algorithm"
        )

        # Check if algorithm is supported
        if algorithm not in self.SUPPORTED_ALGORITHMS:
            supported_algs = ", ".join(self.SUPPORTED_ALGORITHMS)
            raise ValueError(
                f"Unsupported clustering algorithm: {algorithm}. "
                f"Supported algorithms: {supported_algs}"
            )

        # Check if dependencies are available
        if self.nx is None or self.louvain_community is None:
            raise ClusteringException(
                message="Clustering dependencies not available",
                error_code="CLUSTERING_DEPS_MISSING",
                context={
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "algorithm": algorithm,
                },
            )

        # Check cache for recent results
        cache_key = f"{kg_id}:{tenant_id}:{algorithm}"
        if cache_key in self.community_cache:
            cache_entry = self.community_cache[cache_key]
            cache_age = time.time() - cache_entry["timestamp"]

            if cache_age < self.cache_ttl:
                logger.info(f"Using cached communities (age: {cache_age:.2f}s)")
                return cache_entry["communities"]

        try:
            # Get graph data from FalkorDB
            graph_data = self._get_graph_data(kg_id, tenant_id)

            # Check if graph is large enough for clustering
            node_count = len(graph_data["nodes"])
            if node_count < 10:
                logger.info(f"Graph too small for clustering: {node_count} nodes")
                return []

            # Build NetworkX graph from data
            G = self._build_networkx_graph(graph_data)

            # Apply clustering algorithm
            if algorithm == "louvain":
                communities = self._apply_louvain_clustering(G, params)
            elif algorithm == "leiden":
                communities = self._apply_leiden_clustering(G, params)
            elif algorithm == "infomap":
                communities = self._apply_infomap_clustering(G, params)

            # Generate community objects with centroid embeddings
            community_objects = self._generate_community_objects(
                communities, graph_data, kg_id, tenant_id
            )

            # Store communities in FalkorDB
            self._store_communities(community_objects, kg_id, tenant_id)

            # Update cache
            self.community_cache[cache_key] = {
                "communities": community_objects,
                "timestamp": time.time(),
            }

            logger.info(
                f"Computed {len(community_objects)} communities for graph with "
                f"{node_count} nodes using {algorithm} algorithm"
            )

            return community_objects

        except Exception as e:
            logger.error(f"Community computation failed: {str(e)}", exc_info=True)
            raise ClusteringException(
                message=f"Community computation failed: {str(e)}",
                error_code="CLUSTERING_COMPUTATION_ERROR",
                context={
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "algorithm": algorithm,
                },
            ) from e

    def get_community_subgraph(
        self, *, community_id: str, tenant_id: str
    ) -> List[Triple]:
        """Get detailed subgraph for a specific community with on-demand loading.

        Retrieves detailed graph structure for a specific community to enable
        progressive loading and viewport culling for large graph visualization.

        Args:
            community_id: Community identifier for subgraph retrieval
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            List of Triple objects representing community subgraph

        Raises:
            ClusteringException: When subgraph retrieval fails
            ValueError: When community_id is not found
        """
        logger.info(
            f"Retrieving subgraph for community_id={community_id}, tenant_id={tenant_id}"
        )

        try:
            # Extract kg_id from community_id (format: kg_id:community_number)
            parts = community_id.split(":")
            if len(parts) != 2:
                raise ValueError(f"Invalid community_id format: {community_id}")

            kg_id = parts[0]

            # Query FalkorDB for community node
            community_query = """
            MATCH (c:Community {id: $community_id, tenant_id: $tenant_id})
            RETURN c
            """

            community_params = {"community_id": community_id, "tenant_id": tenant_id}

            community_result = self.falkordb.query(
                cypher=community_query,
                kg_id=kg_id,
                tenant_id=tenant_id,
                params=community_params,
            )

            if not community_result["results"]:
                raise ValueError(f"Community not found: {community_id}")

            # Get node IDs in this community
            community_data = community_result["results"][0].get("c", {})
            node_ids = community_data.get("node_ids", [])

            if not node_ids:
                logger.warning(f"Community {community_id} has no nodes")
                return []

            # Query for all triples within this community
            subgraph_query = """
            MATCH (s)-[r]->(o)
            WHERE s.id IN $node_ids AND o.id IN $node_ids
            AND s.tenant_id = $tenant_id AND o.tenant_id = $tenant_id
            RETURN s.id as subject, type(r) as predicate, o.id as object
            """

            subgraph_params = {"node_ids": node_ids, "tenant_id": tenant_id}

            subgraph_result = self.falkordb.query(
                cypher=subgraph_query,
                kg_id=kg_id,
                tenant_id=tenant_id,
                params=subgraph_params,
            )

            # Convert results to Triple objects
            triples = []
            for row in subgraph_result["results"]:
                triple = Triple(
                    subject=row["subject"],
                    predicate=row["predicate"],
                    object=row["object"],
                    tenant_id=tenant_id,
                )
                triples.append(triple)

            logger.info(
                f"Retrieved {len(triples)} triples for community {community_id} "
                f"with {len(node_ids)} nodes"
            )

            return triples

        except ValueError:
            # Re-raise ValueError for invalid community_id
            raise
        except Exception as e:
            logger.error(f"Subgraph retrieval failed: {str(e)}", exc_info=True)
            raise ClusteringException(
                message=f"Subgraph retrieval failed: {str(e)}",
                error_code="CLUSTERING_SUBGRAPH_ERROR",
                context={"community_id": community_id, "tenant_id": tenant_id},
            ) from e

    async def compute_communities_async(
        self, *, kg_id: str, tenant_id: str, algorithm: str = "louvain"
    ) -> List[Community]:
        """Asynchronously compute graph communities for large graphs.

        Offloads community detection to a thread pool for non-blocking operation,
        particularly important for graphs with >50k nodes.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            algorithm: Clustering algorithm name (default: "louvain")

        Returns:
            List of Community objects representing detected clusters

        Raises:
            ClusteringException: When community computation fails
        """
        logger.info(
            f"Asynchronously computing communities for kg_id={kg_id}, "
            f"tenant_id={tenant_id} using {algorithm} algorithm"
        )

        loop = asyncio.get_event_loop()

        try:
            # Offload computation to thread pool
            return await loop.run_in_executor(
                self.executor,
                lambda: self.compute_communities(
                    kg_id=kg_id, tenant_id=tenant_id, algorithm=algorithm
                ),
            )
        except Exception as e:
            logger.error(f"Async community computation failed: {str(e)}", exc_info=True)
            raise ClusteringException(
                message=f"Async community computation failed: {str(e)}",
                error_code="CLUSTERING_ASYNC_ERROR",
                context={
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "algorithm": algorithm,
                },
            ) from e

    def _get_graph_data(self, kg_id: str, tenant_id: str) -> Dict[str, Any]:
        """Retrieve graph data from FalkorDB for clustering.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Dictionary with nodes and edges for graph construction

        Raises:
            ClusteringException: When graph data retrieval fails
        """
        try:
            # Query for nodes
            nodes_query = """
            MATCH (n)
            WHERE n.tenant_id = $tenant_id
            RETURN n.id as id, labels(n) as labels, properties(n) as properties
            """

            nodes_result = self.falkordb.query(
                cypher=nodes_query,
                kg_id=kg_id,
                tenant_id=tenant_id,
                params={"tenant_id": tenant_id},
            )

            # Query for edges
            edges_query = """
            MATCH (s)-[r]->(o)
            WHERE s.tenant_id = $tenant_id AND o.tenant_id = $tenant_id
            RETURN s.id as source, o.id as target, type(r) as type, properties(r) as properties
            """

            edges_result = self.falkordb.query(
                cypher=edges_query,
                kg_id=kg_id,
                tenant_id=tenant_id,
                params={"tenant_id": tenant_id},
            )

            # Process results
            nodes = nodes_result["results"]
            edges = edges_result["results"]

            logger.info(
                f"Retrieved {len(nodes)} nodes and {len(edges)} edges for clustering"
            )

            return {"nodes": nodes, "edges": edges}

        except Exception as e:
            logger.error(f"Graph data retrieval failed: {str(e)}", exc_info=True)
            raise ClusteringException(
                message=f"Graph data retrieval failed: {str(e)}",
                error_code="CLUSTERING_DATA_ERROR",
                context={"kg_id": kg_id, "tenant_id": tenant_id},
            ) from e

    def _build_networkx_graph(self, graph_data: Dict[str, Any]) -> Any:
        """Build NetworkX graph from FalkorDB data.

        Args:
            graph_data: Dictionary with nodes and edges

        Returns:
            NetworkX graph object

        Raises:
            ClusteringException: When graph construction fails
        """
        try:
            G = self.nx.Graph()

            # Add nodes
            for node in graph_data["nodes"]:
                G.add_node(node["id"], **node.get("properties", {}))

            # Add edges
            for edge in graph_data["edges"]:
                G.add_edge(
                    edge["source"],
                    edge["target"],
                    type=edge["type"],
                    **edge.get("properties", {}),
                )

            logger.debug(
                f"Built NetworkX graph with {G.number_of_nodes()} nodes and "
                f"{G.number_of_edges()} edges"
            )

            return G

        except Exception as e:
            logger.error(f"NetworkX graph construction failed: {str(e)}", exc_info=True)
            raise ClusteringException(
                message=f"NetworkX graph construction failed: {str(e)}",
                error_code="CLUSTERING_GRAPH_ERROR",
                context={"node_count": len(graph_data["nodes"])},
            ) from e

    def _apply_louvain_clustering(
        self, G: Any, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, int]:
        """Apply Louvain community detection algorithm.

        Args:
            G: NetworkX graph
            params: Optional algorithm parameters

        Returns:
            Dictionary mapping node IDs to community IDs

        Raises:
            ClusteringException: When clustering fails
        """
        try:
            # Merge default and custom parameters
            effective_params = self.DEFAULT_PARAMS["louvain"].copy()
            if params:
                effective_params.update(params)

            # Apply Louvain algorithm
            communities = self.louvain_community.best_partition(
                G,
                weight=effective_params["weight"],
                resolution=effective_params["resolution"],
                randomize=effective_params["randomize"],
            )

            logger.debug(
                f"Applied Louvain clustering with resolution={effective_params['resolution']}, "
                f"found {len(set(communities.values()))} communities"
            )

            return communities

        except Exception as e:
            logger.error(f"Louvain clustering failed: {str(e)}", exc_info=True)
            raise ClusteringException(
                message=f"Louvain clustering failed: {str(e)}",
                error_code="CLUSTERING_LOUVAIN_ERROR",
                context={"node_count": G.number_of_nodes()},
            ) from e

    def _apply_leiden_clustering(
        self, G: Any, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, int]:
        """Apply Leiden community detection algorithm.

        Args:
            G: NetworkX graph
            params: Optional algorithm parameters

        Returns:
            Dictionary mapping node IDs to community IDs

        Raises:
            ClusteringException: When clustering fails
        """
        try:
            # Check if leidenalg is available
            try:
                import igraph as ig
                import leidenalg
            except ImportError:
                raise ClusteringException(
                    message="Leiden algorithm dependencies not available",
                    error_code="CLUSTERING_LEIDEN_DEPS_MISSING",
                    context={"algorithm": "leiden"},
                )

            # Merge default and custom parameters
            effective_params = self.DEFAULT_PARAMS["leiden"].copy()
            if params:
                effective_params.update(params)

            # Convert NetworkX graph to igraph
            ig_graph = ig.Graph.from_networkx(G)

            # Apply Leiden algorithm
            partition = leidenalg.find_partition(
                ig_graph,
                leidenalg.ModularityVertexPartition,
                weights=effective_params["weight"],
                resolution_parameter=effective_params["resolution"],
                beta=effective_params["beta"],
                n_iterations=effective_params["max_iterations"],
            )

            # Convert result to node_id -> community_id mapping
            communities = {}
            for i, community in enumerate(partition):
                for node_idx in community:
                    node_id = ig_graph.vs[node_idx]["_nx_name"]
                    communities[node_id] = i

            logger.debug(
                f"Applied Leiden clustering with resolution={effective_params['resolution']}, "
                f"found {len(partition)} communities"
            )

            return communities

        except ClusteringException:
            # Re-raise ClusteringException
            raise
        except Exception as e:
            logger.error(f"Leiden clustering failed: {str(e)}", exc_info=True)
            raise ClusteringException(
                message=f"Leiden clustering failed: {str(e)}",
                error_code="CLUSTERING_LEIDEN_ERROR",
                context={"node_count": G.number_of_nodes()},
            ) from e

    def _apply_infomap_clustering(
        self, G: Any, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, int]:
        """Apply Infomap community detection algorithm.

        Args:
            G: NetworkX graph
            params: Optional algorithm parameters

        Returns:
            Dictionary mapping node IDs to community IDs

        Raises:
            ClusteringException: When clustering fails
        """
        try:
            # Check if infomap is available
            try:
                import infomap
            except ImportError:
                raise ClusteringException(
                    message="Infomap algorithm dependencies not available",
                    error_code="CLUSTERING_INFOMAP_DEPS_MISSING",
                    context={"algorithm": "infomap"},
                )

            # Merge default and custom parameters
            effective_params = self.DEFAULT_PARAMS["infomap"].copy()
            if params:
                effective_params.update(params)

            # Initialize Infomap
            im = infomap.Infomap("--two-level")

            # Add nodes and edges
            for i, node in enumerate(G.nodes()):
                im.add_node(i, node)

            for edge in G.edges(data=True):
                source, target = edge[0], edge[1]
                weight = (
                    edge[2].get(effective_params["weight"], 1.0)
                    if effective_params["weight"]
                    else 1.0
                )
                source_idx = list(G.nodes()).index(source)
                target_idx = list(G.nodes()).index(target)
                im.add_link(source_idx, target_idx, weight)

            # Run Infomap
            im.run(num_trials=effective_params["num_trials"])

            # Extract communities
            communities = {}
            for node in im.tree:
                if node.is_leaf:
                    node_id = node.node_id
                    community_id = node.module_id
                    original_id = list(G.nodes())[node_id]
                    communities[original_id] = community_id

            logger.debug(
                f"Applied Infomap clustering with num_trials={effective_params['num_trials']}, "
                f"found {len(set(communities.values()))} communities"
            )

            return communities

        except ClusteringException:
            # Re-raise ClusteringException
            raise
        except Exception as e:
            logger.error(f"Infomap clustering failed: {str(e)}", exc_info=True)
            raise ClusteringException(
                message=f"Infomap clustering failed: {str(e)}",
                error_code="CLUSTERING_INFOMAP_ERROR",
                context={"node_count": G.number_of_nodes()},
            ) from e

    def _generate_community_objects(
        self,
        communities: Dict[str, int],
        graph_data: Dict[str, Any],
        kg_id: str,
        tenant_id: str,
    ) -> List[Community]:
        """Generate Community objects with centroid embeddings.

        Args:
            communities: Dictionary mapping node IDs to community IDs
            graph_data: Dictionary with nodes and edges
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            List of Community objects

        Raises:
            ClusteringException: When community generation fails
        """
        try:
            # Group nodes by community
            community_nodes = {}
            for node_id, community_id in communities.items():
                if community_id not in community_nodes:
                    community_nodes[community_id] = []
                community_nodes[community_id].append(node_id)

            # Filter out small communities
            filtered_communities = {
                comm_id: nodes
                for comm_id, nodes in community_nodes.items()
                if len(nodes) >= self.min_community_size
            }

            if len(filtered_communities) < len(community_nodes):
                logger.info(
                    f"Filtered out {len(community_nodes) - len(filtered_communities)} "
                    f"communities with fewer than {self.min_community_size} nodes"
                )

            # Generate embeddings for each community
            community_objects = []

            for comm_id, node_ids in filtered_communities.items():
                # Generate community ID
                community_id = f"{kg_id}:{comm_id}"

                # Generate centroid embedding
                centroid_embedding = self._generate_centroid_embedding(
                    node_ids, graph_data["nodes"]
                )

                # Create Community object
                community = Community(
                    id=community_id,
                    centroid_embedding=centroid_embedding,
                    node_ids=node_ids,
                    size=len(node_ids),
                    tenant_id=tenant_id,
                )

                community_objects.append(community)

            logger.info(f"Generated {len(community_objects)} community objects")
            return community_objects

        except Exception as e:
            logger.error(f"Community object generation failed: {str(e)}", exc_info=True)
            raise ClusteringException(
                message=f"Community object generation failed: {str(e)}",
                error_code="CLUSTERING_OBJECT_ERROR",
                context={
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "community_count": len(set(communities.values())),
                },
            ) from e

    def _generate_centroid_embedding(
        self, node_ids: List[str], nodes: List[Dict[str, Any]]
    ) -> List[float]:
        """Generate centroid embedding for a community.

        Args:
            node_ids: List of node IDs in the community
            nodes: List of node data dictionaries

        Returns:
            List of floats representing centroid embedding

        Raises:
            ClusteringException: When embedding generation fails
        """
        try:
            # If PCA is not available, return random embedding
            if self.pca is None:
                return list(np.random.rand(self.embedding_dimensions).astype(float))

            # Get node properties for embedding generation
            node_properties = []
            for node in nodes:
                if node["id"] in node_ids:
                    # Extract numeric properties for embedding
                    props = {}
                    for key, value in node.get("properties", {}).items():
                        if isinstance(value, (int, float)):
                            props[key] = value

                    node_properties.append(props)

            # If no numeric properties, generate random embedding
            if not node_properties or not any(props for props in node_properties):
                return list(np.random.rand(self.embedding_dimensions).astype(float))

            # Convert properties to feature matrix
            feature_names = set()
            for props in node_properties:
                feature_names.update(props.keys())

            feature_names = sorted(feature_names)
            feature_matrix = np.zeros((len(node_properties), len(feature_names)))

            for i, props in enumerate(node_properties):
                for j, feature in enumerate(feature_names):
                    feature_matrix[i, j] = props.get(feature, 0.0)

            # Apply PCA for dimensionality reduction
            if feature_matrix.shape[1] > self.embedding_dimensions:
                pca = self.pca(n_components=self.embedding_dimensions)
                reduced_matrix = pca.fit_transform(feature_matrix)
                centroid = np.mean(reduced_matrix, axis=0)
            else:
                # If fewer features than dimensions, pad with zeros
                centroid = np.mean(feature_matrix, axis=0)
                if len(centroid) < self.embedding_dimensions:
                    padding = np.zeros(self.embedding_dimensions - len(centroid))
                    centroid = np.concatenate([centroid, padding])

            # Normalize centroid
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm

            return list(centroid.astype(float))

        except Exception as e:
            logger.error(
                f"Centroid embedding generation failed: {str(e)}", exc_info=True
            )
            # Return random embedding as fallback
            return list(np.random.rand(self.embedding_dimensions).astype(float))

    def _store_communities(
        self, communities: List[Community], kg_id: str, tenant_id: str
    ) -> None:
        """Store communities in FalkorDB for progressive loading.

        Args:
            communities: List of Community objects
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Raises:
            ClusteringException: When community storage fails
        """
        try:
            # Clear existing communities for this knowledge graph
            clear_query = """
            MATCH (c:Community)
            WHERE c.kg_id = $kg_id AND c.tenant_id = $tenant_id
            DETACH DELETE c
            """

            self.falkordb.query(
                cypher=clear_query,
                kg_id=kg_id,
                tenant_id=tenant_id,
                params={"kg_id": kg_id, "tenant_id": tenant_id},
            )

            # Store each community
            for community in communities:
                store_query = """
                CREATE (c:Community {
                    id: $id,
                    kg_id: $kg_id,
                    tenant_id: $tenant_id,
                    size: $size,
                    centroid_embedding: $centroid_embedding,
                    node_ids: $node_ids,
                    created_at: $created_at
                })
                RETURN c
                """

                self.falkordb.query(
                    cypher=store_query,
                    kg_id=kg_id,
                    tenant_id=tenant_id,
                    params={
                        "id": community.id,
                        "kg_id": kg_id,
                        "tenant_id": tenant_id,
                        "size": community.size,
                        "centroid_embedding": community.centroid_embedding,
                        "node_ids": community.node_ids,
                        "created_at": datetime.now().isoformat(),
                    },
                )

            logger.info(f"Stored {len(communities)} communities in FalkorDB")

        except Exception as e:
            logger.error(f"Community storage failed: {str(e)}", exc_info=True)
            raise ClusteringException(
                message=f"Community storage failed: {str(e)}",
                error_code="CLUSTERING_STORAGE_ERROR",
                context={
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "community_count": len(communities),
                },
            ) from e
