"""Enhanced Memgraph adapter with MAGE algorithms and streaming."""

import logging
from datetime import datetime
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional, Union

from application.ports.graph import GraphRetrieverPort
from application.ports.messaging import MessageBusPort
from domain.entities import Triple
from domain.services import GraphRAGException

logger = logging.getLogger(__name__)


class MemgraphGraphRAGAdapter(GraphRetrieverPort):
    """Adapter for Memgraph 3.0 native GraphRAG integration.

    Implements GraphRetrieverPort to provide document indexing and natural language
    query capabilities using Memgraph's native AgenticGraphRagEngine. Supports
    advanced agent coordination and native graph capabilities.
    """

    def __init__(
        self,
        memgraph_connection_string: str,
        message_bus: Optional[MessageBusPort] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize MemgraphGraphRAGAdapter with configuration.

        Args:
            memgraph_connection_string: Connection string for Memgraph database
            message_bus: Optional MessageBusPort for agent coordination
            config: Optional configuration parameters for Memgraph GraphRAG

        Raises:
            GraphRAGException: When Memgraph connection fails or AgenticGraphRagEngine is unavailable
        """
        self.connection_string = memgraph_connection_string
        self.message_bus = message_bus
        self.config = config or {}

        try:
            # Import Memgraph libraries here to avoid global dependency
            # This allows the adapter to be instantiated even if Memgraph
            # libraries are not installed in the environment
            from memgraph.agentic import AgenticGraphRagEngine, MemgraphClient

            # Initialize Memgraph client
            self.client = MemgraphClient(self.connection_string)

            # Initialize AgenticGraphRagEngine
            self.engine = AgenticGraphRagEngine(
                client=self.client, **self._get_engine_config()
            )

            logger.info(
                f"Successfully connected to Memgraph at {memgraph_connection_string}"
            )

        except ImportError as e:
            logger.error("Failed to import Memgraph libraries", exc_info=True)
            raise GraphRAGException(
                message="Memgraph libraries not installed. Please install memgraph-python package.",
                error_code="MEMGRAPH_IMPORT_ERROR",
                context={"error": str(e)},
            ) from e

        except Exception as e:
            logger.error(
                f"Failed to initialize Memgraph connection: {str(e)}", exc_info=True
            )
            raise GraphRAGException(
                message=f"Failed to initialize Memgraph connection: {str(e)}",
                error_code="MEMGRAPH_CONNECTION_ERROR",
                context={"connection_string": memgraph_connection_string},
            ) from e

    def index(self, *, docs: List[str], kg_id: str, tenant_id: str) -> List[Triple]:
        """Extract entities and relationships from documents using Memgraph's native capabilities.

        Processes documents through Memgraph's AgenticGraphRagEngine to extract
        structured knowledge in the form of subject-predicate-object triples.

        Args:
            docs: List of document content strings to process
            kg_id: Knowledge graph identifier for storage context
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            List of Triple objects representing extracted knowledge

        Raises:
            GraphRAGException: When document processing fails
            ValueError: When extracted triples are malformed
        """
        logger.info(
            f"Indexing {len(docs)} documents for kg_id={kg_id}, tenant_id={tenant_id} using Memgraph"
        )

        try:
            # Create document metadata with tenant and kg information
            documents_with_metadata = [
                {
                    "content": doc,
                    "metadata": {
                        "kg_id": kg_id,
                        "tenant_id": tenant_id,
                        "timestamp": datetime.now().isoformat(),
                    },
                }
                for doc in docs
            ]

            # Use Memgraph's native indexing capabilities
            result = self.engine.index_documents(
                documents=documents_with_metadata, kg_id=kg_id, tenant_filter=tenant_id
            )

            # Convert Memgraph triples to domain Triple objects
            triples = self._convert_to_domain_triples(
                result.get("triples", []), tenant_id
            )

            logger.info(f"Successfully extracted {len(triples)} triples using Memgraph")
            return triples

        except Exception as e:
            logger.error(f"Memgraph indexing failed: {str(e)}", exc_info=True)
            raise GraphRAGException(
                message=f"Memgraph indexing failed: {str(e)}",
                error_code="MEMGRAPH_INDEX_ERROR",
                context={
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "doc_count": len(docs),
                },
            ) from e

    def run(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, List[Triple]]:
        """Execute natural language query against knowledge graph using Memgraph.

        Processes natural language questions using Memgraph's AgenticGraphRagEngine
        to retrieve relevant information from the knowledge graph.

        Args:
            question: Natural language query string
            kg_id: Knowledge graph identifier to query against
            tenant_id: Tenant identifier for multi-tenant isolation
            opts: Optional tuning parameters including:
                - max_hops: Maximum graph traversal depth (default: 2)
                - context_tokens: Maximum context window size (default: 4096)
                - return_triples: Return structured triples vs text (default: False)
                - include_reasoning: Include reasoning explanation (default: True)
                - agent_mode: Enable multi-agent coordination (default: False)

        Returns:
            Query results as formatted text or structured Triple list
            depending on opts.return_triples setting

        Raises:
            GraphRAGException: When query execution fails
            ValueError: When query parameters are invalid
        """
        logger.info(
            f"Executing query for kg_id={kg_id}, tenant_id={tenant_id} using Memgraph: {question[:50]}..."
        )

        # Set default options
        options = {
            "max_hops": 2,
            "context_tokens": 4096,
            "return_triples": False,
            "include_reasoning": True,
            "agent_mode": False,
        }
        if opts:
            options.update(opts)

        start_time = datetime.now()

        try:
            # Configure query parameters
            query_params = {
                "question": question,
                "kg_id": kg_id,
                "tenant_id": tenant_id,
                "max_hops": options.get("max_hops", 2),
                "context_tokens": options.get("context_tokens", 4096),
                "include_reasoning": options.get("include_reasoning", True),
            }

            # Use agent coordination if enabled and message bus is available
            if options.get("agent_mode", False) and self.message_bus:
                result = self._execute_agent_query(query_params)
            else:
                # Use direct query execution
                result = self.engine.query(**query_params)

            # Calculate execution time
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.debug(f"Query execution time: {execution_time_ms:.2f}ms")

            # Return results based on requested format
            if options.get("return_triples", False):
                # Return structured triples
                triples = self._convert_to_domain_triples(
                    result.get("triples", []), tenant_id
                )
                logger.info(f"Query returned {len(triples)} triples")
                return triples
            else:
                # Return formatted text response
                response = self._format_text_response(result)
                logger.info(f"Query returned text response of length {len(response)}")
                return response

        except Exception as e:
            logger.error(f"Memgraph query failed: {str(e)}", exc_info=True)
            raise GraphRAGException(
                message=f"Memgraph query failed: {str(e)}",
                error_code="MEMGRAPH_QUERY_ERROR",
                context={
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "question": question[:100],
                },
            ) from e

    def _get_engine_config(self) -> Dict[str, Any]:
        """Get configuration for AgenticGraphRagEngine.

        Returns:
            Configuration dictionary for engine initialization
        """
        # Start with default configuration
        engine_config = {
            "embedding_model": "text-embedding-ada-002",
            "llm_model": "gpt-4",
            "max_tokens": 4096,
            "temperature": 0.7,
        }

        # Override with user-provided configuration
        if "engine" in self.config:
            engine_config.update(self.config["engine"])

        return engine_config

    def _convert_to_domain_triples(
        self, memgraph_triples: List[Dict[str, Any]], tenant_id: str
    ) -> List[Triple]:
        """Convert Memgraph triples to domain Triple objects.

        Args:
            memgraph_triples: List of triples from Memgraph
            tenant_id: Tenant identifier for Triple objects

        Returns:
            List of domain Triple objects
        """
        domain_triples = []

        for triple_data in memgraph_triples:
            # Ensure required fields are present
            if not all(k in triple_data for k in ["subject", "predicate", "object"]):
                logger.warning(f"Skipping malformed triple: {triple_data}")
                continue

            # Create domain Triple object
            triple = Triple(
                subject=triple_data["subject"],
                predicate=triple_data["predicate"],
                object=triple_data["object"],
                tenant_id=tenant_id,
            )
            domain_triples.append(triple)

        return domain_triples

    def _format_text_response(self, result: Dict[str, Any]) -> str:
        """Format text response from Memgraph query result.

        Args:
            result: Memgraph query result

        Returns:
            Formatted text response
        """
        # Extract main response
        if "response" in result:
            response = result["response"]
        else:
            response = "No direct answer found."

        # Include reasoning if available
        if "reasoning" in result:
            response = f"{response}\n\nReasoning:\n{result['reasoning']}"

        # Include path information if available
        if "path" in result:
            path_info = self._format_path_info(result["path"])
            if path_info:
                response = f"{response}\n\nPath Information:\n{path_info}"

        return response

    def _format_path_info(self, path_data: Any) -> str:
        """Format path information for text response.

        Args:
            path_data: Path data from query result

        Returns:
            Formatted path information string
        """
        if not path_data:
            return ""

        # Handle different path data formats
        if isinstance(path_data, str):
            return path_data

        if isinstance(path_data, list):
            path_steps = []
            for i, step in enumerate(path_data):
                if isinstance(step, dict):
                    if "node" in step:
                        path_steps.append(f"Node: {step['node']}")
                    elif "edge" in step:
                        path_steps.append(f"Edge: {step['edge']}")
                    else:
                        path_steps.append(f"Step {i+1}: {step}")
                else:
                    path_steps.append(f"Step {i+1}: {step}")

            return "\n".join(path_steps)

        # Default case for unknown format
        return str(path_data)

    def _execute_agent_query(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute query using multi-agent coordination.

        Uses MessageBusPort to coordinate multiple agents for complex queries
        that require collaborative reasoning and graph exploration.

        Args:
            query_params: Query parameters

        Returns:
            Query result with agent coordination
        """
        if not self.message_bus:
            raise ValueError("MessageBusPort is required for agent mode")

        question = query_params["question"]
        kg_id = query_params["kg_id"]
        tenant_id = query_params["tenant_id"]

        # Generate unique conversation ID for this query
        conversation_id = f"memgraph-query-{kg_id}-{datetime.now().timestamp()}"

        # Publish query to agent coordination topic
        self.message_bus.publish(
            topic="agent.coordination.query",
            message={
                "conversation_id": conversation_id,
                "question": question,
                "kg_id": kg_id,
                "query_params": query_params,
            },
            tenant_id=tenant_id,
        )

        # Execute query with agent coordination enabled
        result = self.engine.query(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            agent_coordination=True,
            **{
                k: v
                for k, v in query_params.items()
                if k not in ["question", "kg_id", "tenant_id"]
            },
        )

        # Publish query result for other agents
        self.message_bus.publish(
            topic="agent.coordination.result",
            message={"conversation_id": conversation_id, "result": result},
            tenant_id=tenant_id,
        )

        return result


try:
    import mgp

    MGP_AVAILABLE = True
except ImportError:
    MGP_AVAILABLE = False
    mgp = None


class MemgraphMageAdapter:
    def __init__(
        self,
        memgraph_connection_string: str,
        enable_mage: bool = True,
        stream_enabled: bool = True,
    ):
        if not MGP_AVAILABLE:
            raise ImportError("mgp library is required for Memgraph adapter")

        self.connection_string = memgraph_connection_string
        self.enable_mage = enable_mage
        self.stream_enabled = stream_enabled

        # Parse connection string
        parsed = urlparse(memgraph_connection_string)

        self.driver = mgp.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 7687,
            username=parsed.username or "",
            password=parsed.password or "",
        )

    async def execute_mage_algorithm(
        self, algorithm: str, parameters: Dict[str, Any], graph_name: str = "default"
    ) -> Dict[str, Any]:
        """Execute MAGE (Memgraph Advanced Graph Extensions) algorithms."""
        if not self.enable_mage:
            raise RuntimeError("MAGE algorithms not enabled")

        algorithm_map = {
            "pagerank": "CALL pagerank.get() YIELD node, rank RETURN node, rank ORDER BY rank DESC",
            "betweenness": "CALL betweenness_centrality.get() YIELD node, betweenness RETURN node, betweenness ORDER BY betweenness DESC",
            "closeness": "CALL closeness_centrality.get() YIELD node, closeness RETURN node, closeness ORDER BY closeness DESC",
            "louvain": "CALL community_detection.get() YIELD node, community_id RETURN node, community_id",
            "label_propagation": "CALL label_propagation.get() YIELD node, community_id RETURN node, community_id",
            "weakly_connected": "CALL weakly_connected_components.get() YIELD node, component_id RETURN node, component_id",
        }

        if algorithm not in algorithm_map:
            raise ValueError(f"Unsupported MAGE algorithm: {algorithm}")

        try:
            query = algorithm_map[algorithm]

            # Add parameters if provided
            if parameters:
                param_string = ", ".join([f"{k}: {v}" for k, v in parameters.items()])
                query = query.replace("()", f"({param_string})")

            results = []
            with self.driver.session() as session:
                result = session.run(query)
                for record in result:
                    results.append(dict(record))

            return {
                "algorithm": algorithm,
                "parameters": parameters,
                "results": results,
                "count": len(results),
            }

        except Exception as e:
            logger.error(f"MAGE algorithm execution error: {e}")
            raise RuntimeError(f"MAGE {algorithm} failed: {e}")

    async def setup_streaming_triggers(self, graph_name: str = "default") -> bool:
        """Setup real-time streaming triggers for graph changes."""
        if not self.stream_enabled:
            return False

        triggers = [
            """
            CREATE TRIGGER node_insert_trigger
            ON () CREATE
            EXECUTE CALL streaming.publish('graph_changes', 'node_created', createdVertex);
            """,
            """
            CREATE TRIGGER relationship_insert_trigger
            ON ()-[]->() CREATE
            EXECUTE CALL streaming.publish('graph_changes', 'relationship_created', createdEdge);
            """,
            """
            CREATE TRIGGER node_update_trigger
            ON () UPDATE
            EXECUTE CALL streaming.publish('graph_changes', 'node_updated', updatedVertex);
            """,
        ]

        try:
            with self.driver.session() as session:
                for trigger in triggers:
                    session.run(trigger)
            logger.info("Streaming triggers configured successfully")
            return True
        except Exception as e:
            logger.error(f"Streaming trigger setup failed: {e}")
            return False

    async def graph_projection_create(
        self,
        projection_name: str,
        node_filter: str = "*",
        relationship_filter: str = "*",
    ) -> bool:
        """Create graph projections for algorithm execution."""
        query = f"""
        CALL gds.graph.project(
            '{projection_name}',
            '{node_filter}',
            '{relationship_filter}'
        ) YIELD graphName, nodeCount, relationshipCount
        RETURN graphName, nodeCount, relationshipCount
        """

        try:
            with self.driver.session() as session:
                result = session.run(query)
                record = result.single()
                logger.info(
                    f"Created projection {projection_name}: {record['nodeCount']} nodes, {record['relationshipCount']} relationships"
                )
                return True
        except Exception as e:
            logger.error(f"Graph projection creation failed: {e}")
            return False

    async def temporal_graph_query(
        self,
        start_time: datetime,
        end_time: datetime,
        entity_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query temporal graph data with time-based filtering."""
        time_filter = f"n.timestamp >= datetime('{start_time.isoformat()}') AND n.timestamp <= datetime('{end_time.isoformat()}')"

        if entity_filter:
            query = f"""
            MATCH (n:{entity_filter})-[r]-(m)
            WHERE {time_filter}
            RETURN n, r, m, n.timestamp as timestamp
            ORDER BY timestamp DESC
            """
        else:
            query = f"""
            MATCH (n)-[r]-(m)
            WHERE {time_filter}
            RETURN n, r, m, n.timestamp as timestamp
            ORDER BY timestamp DESC
            """

        try:
            results = []
            with self.driver.session() as session:
                result = session.run(query)
                for record in result:
                    results.append(
                        {
                            "source": dict(record["n"]),
                            "relationship": dict(record["r"]),
                            "target": dict(record["m"]),
                            "timestamp": record["timestamp"],
                        }
                    )
            return results
        except Exception as e:
            logger.error(f"Temporal query error: {e}")
            return []
