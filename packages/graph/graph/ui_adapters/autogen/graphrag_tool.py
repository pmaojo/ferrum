"""AutoGen Studio tool registration for GraphRAG integration.

This module provides the necessary components to integrate GraphRAG functionality
with AutoGen Studio's multi-agent framework, including tool registration and
agent coordination through MessageBusPort.

Requirements addressed:
- 10.3: Register GraphRAG as a PythonTool within agent workflows
- 6.1: Multi-agent collaboration through message passing
"""

from typing import Dict, Any, Optional, List, Callable, Union
import logging
import uuid
import threading
from datetime import datetime
from functools import wraps

from application.ports import GraphRetrieverPort, MessageBusPort, TracingPort
from domain.entities import Triple

# Setup logging
logger = logging.getLogger(__name__)


class ResponseAwaiter:
    """Utility to wait for a single message on a topic."""

    def __init__(
        self,
        message_bus: MessageBusPort,
        *,
        topic: str,
        tenant_id: str,
        id_field: str,
        match_id: str,
    ) -> None:
        self._message_bus = message_bus
        self._event = threading.Event()
        self._result: Optional[Dict[str, Any]] = None

        def handler(msg: Dict[str, Any]) -> None:
            if msg.get(id_field) == match_id and not self._event.is_set():
                self._result = msg
                self._event.set()

        self._message_bus.subscribe(topic=topic, handler=handler, tenant_id=tenant_id)

    def wait(self, timeout: float) -> Optional[Dict[str, Any]]:
        self._event.wait(timeout)
        return self._result


class GraphRAGToolRegistry:
    """Registry for GraphRAG tools in AutoGen Studio.

    Manages the registration and coordination of GraphRAG tools within
    AutoGen Studio's multi-agent framework, providing a bridge between
    the domain services and AutoGen's tool system.
    """

    def __init__(
        self,
        retriever: GraphRetrieverPort,
        message_bus: MessageBusPort,
        tracer: Optional[TracingPort] = None
    ):
        """Initialize the GraphRAG tool registry.

        Args:
            retriever: GraphRAG port for knowledge graph operations
            message_bus: Message bus for agent coordination
            tracer: Optional tracing port for observability
        """
        self.retriever = retriever
        self.message_bus = message_bus
        self.tracer = tracer
        self.registered_agents = {}

        # Subscribe to agent coordination messages
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Set up message handlers for agent coordination."""
        try:
            self.message_bus.subscribe(
                topic="agents.graphrag.query.response",
                handler=self._handle_query_response,
                tenant_id="*"  # Subscribe to all tenants
            )

            self.message_bus.subscribe(
                topic="agents.graphrag.index.response",
                handler=self._handle_index_response,
                tenant_id="*"  # Subscribe to all tenants
            )

            logger.info("GraphRAG message handlers registered successfully")

        except Exception as e:
            logger.error(f"Failed to set up message handlers: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to set up message handlers: {str(e)}")

    def _handle_query_response(self, message: Dict[str, Any]) -> None:
        """Handle query response messages from other agents.

        Args:
            message: Response message containing query results
        """
        query_id = message.get("query_id")
        agent_id = message.get("agent_id")
        tenant_id = message.get("tenant_id")

        if self.tracer:
            self.tracer.start_span(
                name="graphrag_tool.handle_query_response",
                tenant_id=tenant_id,
                query_id=query_id,
                agent_id=agent_id
            )

        logger.debug(f"Received query response for query_id={query_id}, agent_id={agent_id}")

        # Notify any waiting agents about the response
        response_topic = f"agents.{agent_id}.response"
        self.message_bus.publish(
            topic=response_topic,
            message=message,
            tenant_id=tenant_id,
            idempotency_key=f"response_{query_id}"
        )

    def _handle_index_response(self, message: Dict[str, Any]) -> None:
        """Handle index response messages from other agents.

        Args:
            message: Response message containing indexing results
        """
        index_id = message.get("index_id")
        agent_id = message.get("agent_id")
        tenant_id = message.get("tenant_id")

        if self.tracer:
            self.tracer.start_span(
                name="graphrag_tool.handle_index_response",
                tenant_id=tenant_id,
                index_id=index_id,
                agent_id=agent_id
            )

        logger.debug(f"Received index response for index_id={index_id}, agent_id={agent_id}")

        # Notify any waiting agents about the response
        response_topic = f"agents.{agent_id}.response"
        self.message_bus.publish(
            topic=response_topic,
            message=message,
            tenant_id=tenant_id,
            idempotency_key=f"response_{index_id}"
        )

    def register_agent(
        self,
        agent_id: str,
        tenant_id: str,
        capabilities: List[str] = ["query", "index"]
    ) -> None:
        """Register an agent for GraphRAG tool usage.

        Args:
            agent_id: Unique identifier for the agent
            tenant_id: Tenant identifier for multi-tenant isolation
            capabilities: List of capabilities to enable for this agent
        """
        if self.tracer:
            self.tracer.start_span(
                name="graphrag_tool.register_agent",
                tenant_id=tenant_id,
                agent_id=agent_id,
                capabilities=capabilities
            )

        logger.info(f"Registering agent: id={agent_id}, tenant_id={tenant_id}, capabilities={capabilities}")

        self.registered_agents[agent_id] = {
            "tenant_id": tenant_id,
            "capabilities": capabilities,
            "registered_at": datetime.utcnow(),
        }

        # Subscribe to agent-specific messages
        agent_topic = f"agents.{agent_id}.request"
        try:
            self.message_bus.subscribe(
                topic=agent_topic,
                handler=lambda msg: self._handle_agent_request(msg, agent_id),
                tenant_id=tenant_id
            )
            logger.debug(f"Subscribed to agent topic: {agent_topic}")
        except Exception as e:
            logger.error(f"Failed to subscribe to agent topic: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to subscribe to agent topic: {str(e)}")

    def _handle_agent_request(self, message: Dict[str, Any], agent_id: str) -> None:
        """Handle requests from registered agents.

        Args:
            message: Request message from agent
            agent_id: Agent identifier
        """
        request_type = message.get("request_type")
        tenant_id = message.get("tenant_id")

        if self.tracer:
            self.tracer.start_span(
                name="graphrag_tool.handle_agent_request",
                tenant_id=tenant_id,
                agent_id=agent_id,
                request_type=request_type
            )

        logger.debug(f"Handling agent request: agent_id={agent_id}, request_type={request_type}")

        if request_type == "query":
            self._process_query_request(message, agent_id)
        elif request_type == "index":
            self._process_index_request(message, agent_id)
        else:
            logger.warning(f"Unknown request type: {request_type}")

    def _process_query_request(self, message: Dict[str, Any], agent_id: str) -> None:
        """Process a query request from an agent.

        Args:
            message: Query request message
            agent_id: Agent identifier
        """
        question = message.get("question")
        kg_id = message.get("kg_id", "default")
        tenant_id = message.get("tenant_id")
        query_id = message.get("query_id", uuid.uuid4().hex)
        opts = message.get("opts", {})

        # Set SDK-optimized options
        sdk_opts = {
            "return_formatted": True,
            "include_reasoning": True,
            "include_metadata": True,
            **opts
        }

        try:
            # Execute query using GraphRetrieverPort (now SDK-powered)
            result = self.retriever.run(
                question=question,
                kg_id=kg_id,
                tenant_id=tenant_id,
                opts=sdk_opts
            )

            # Publish response
            response_topic = f"agents.{agent_id}.response"
            self.message_bus.publish(
                topic=response_topic,
                message={
                    "query_id": query_id,
                    "agent_id": agent_id,
                    "tenant_id": tenant_id,
                    "status": "completed",
                    "result": result,
                    "question": question
                },
                tenant_id=tenant_id,
                idempotency_key=f"response_{query_id}"
            )

            logger.info(f"Query processed successfully: query_id={query_id}, agent_id={agent_id}")

        except Exception as e:
            logger.error(f"Failed to process query: {str(e)}", exc_info=True)

            # Publish error response
            response_topic = f"agents.{agent_id}.response"
            self.message_bus.publish(
                topic=response_topic,
                message={
                    "query_id": query_id,
                    "agent_id": agent_id,
                    "tenant_id": tenant_id,
                    "status": "failed",
                    "error": str(e),
                    "question": question
                },
                tenant_id=tenant_id,
                idempotency_key=f"response_{query_id}"
            )

    def _process_index_request(self, message: Dict[str, Any], agent_id: str) -> None:
        """Process an index request from an agent.

        Args:
            message: Index request message
            agent_id: Agent identifier
        """
        docs = message.get("docs", [])
        kg_id = message.get("kg_id", "default")
        tenant_id = message.get("tenant_id")
        index_id = message.get("index_id", uuid.uuid4().hex)

        try:
            # Execute indexing using GraphRetrieverPort
            triples = self.retriever.index(
                docs=docs,
                kg_id=kg_id,
                tenant_id=tenant_id
            )

            # Convert Triple objects to dictionaries for serialization
            triple_dicts = [
                {"subject": t.subject, "predicate": t.predicate, "object": t.object}
                for t in triples
            ]

            # Publish response
            response_topic = f"agents.{agent_id}.response"
            self.message_bus.publish(
                topic=response_topic,
                message={
                    "index_id": index_id,
                    "agent_id": agent_id,
                    "tenant_id": tenant_id,
                    "status": "completed",
                    "triples": triple_dicts,
                    "triple_count": len(triples)
                },
                tenant_id=tenant_id,
                idempotency_key=f"response_{index_id}"
            )

            logger.info(f"Indexing processed successfully: index_id={index_id}, agent_id={agent_id}, triple_count={len(triples)}")

        except Exception as e:
            logger.error(f"Failed to process indexing: {str(e)}", exc_info=True)

            # Publish error response
            response_topic = f"agents.{agent_id}.response"
            self.message_bus.publish(
                topic=response_topic,
                message={
                    "index_id": index_id,
                    "agent_id": agent_id,
                    "tenant_id": tenant_id,
                    "status": "failed",
                    "error": str(e),
                    "doc_count": len(docs)
                },
                tenant_id=tenant_id,
                idempotency_key=f"response_{index_id}"
            )


# Tool decorator for AutoGen Studio integration
def tool(func: Callable) -> Callable:
    """Decorator to register a function as an AutoGen Studio tool.

    Args:
        func: Function to decorate

    Returns:
        Decorated function with AutoGen Studio tool metadata
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    # Add AutoGen Studio tool metadata
    wrapper._tool = True
    wrapper._tool_name = getattr(func, "__name__", "graphrag_tool")
    wrapper._tool_description = getattr(func, "__doc__", "GraphRAG knowledge graph tool")

    return wrapper


# Main tool function for AutoGen Studio integration
@tool
def ask_graphrag(
    question: str,
    kg_id: str = "default",
    tenant_id: str = "default",
    agent_id: str = None,
    opts: Dict[str, Any] = None,
    _registry: Optional["GraphRAGToolRegistry"] = None,
) -> Union[str, Dict[str, Any]]:
    """Query the knowledge graph using natural language with advanced GraphRAG capabilities.

    Enhanced Features:
    - Multi-hop reasoning across entity relationships
    - Confidence scoring for retrieved information
    - Real-time ontology validation during queries
    - Cross-KG federated search capabilities
    - Temporal reasoning for time-sensitive queries

    Args:
        question: Natural language query to execute
        kg_id: Knowledge graph identifier (default: "default")
        tenant_id: Tenant identifier (default: "default")
        agent_id: Agent identifier (default: auto-generated)
        opts: Advanced query options:
            - reasoning_depth: Maximum inference steps (1-5)
            - confidence_threshold: Minimum confidence for results (0.0-1.0)
            - temporal_scope: Time range for temporal queries ("1d", "1w", "1m")
            - cross_kg_search: Enable federated search across multiple KGs
            - explanation_detail: Level of reasoning explanation ("basic", "detailed", "full")
            - ontology_validation: Validate results against current ontology
            - real_time_updates: Include live graph updates in results

    Returns:
        Enhanced query results with confidence scores and explanations

    Raises:
        ValueError: When query execution fails
    """
    registry = _registry
    if registry is None:
        raise ValueError(
            "GraphRAGToolRegistry instance required. Use register_with_autogen to bind."
        )

    return _ask_graphrag_impl(
        question=question,
        kg_id=kg_id,
        tenant_id=tenant_id,
        agent_id=agent_id,
        opts=opts,
        registry=registry,
    )


def _ask_graphrag_impl(
    *,
    question: str,
    kg_id: str,
    tenant_id: str,
    agent_id: Optional[str],
    opts: Optional[Dict[str, Any]],
    registry: "GraphRAGToolRegistry",
) -> Union[str, Dict[str, Any]]:
    """Internal implementation for executing a GraphRAG query."""

    if not agent_id:
        agent_id = f"autogen_{uuid.uuid4().hex[:8]}"

    if agent_id not in registry.registered_agents:
        registry.register_agent(agent_id=agent_id, tenant_id=tenant_id)

    query_id = f"query_{uuid.uuid4().hex}"

    request = {
        "request_type": "query",
        "query_id": query_id,
        "agent_id": agent_id,
        "tenant_id": tenant_id,
        "question": question,
        "kg_id": kg_id,
        "opts": opts or {},
    }

    response_topic = f"agents.{agent_id}.response"
    awaiter = ResponseAwaiter(
        registry.message_bus,
        topic=response_topic,
        tenant_id=tenant_id,
        id_field="query_id",
        match_id=query_id,
    )

    registry.message_bus.publish(
        topic=f"agents.{agent_id}.request",
        message=request,
        tenant_id=tenant_id,
        idempotency_key=query_id,
    )

    timeout = (opts or {}).get("timeout", 5.0)
    response = awaiter.wait(timeout)
    if response is None:
        raise TimeoutError(f"No response received for query_id={query_id}")

    if response.get("status") != "completed":
        error_msg = response.get("error", "unknown error")
        raise ValueError(f"GraphRAG query failed: {error_msg}")

    return response.get("result")


# Function to create a properly bound ask_graphrag tool
def create_ask_graphrag_tool(registry: GraphRAGToolRegistry) -> Callable:
    """Create a properly bound ask_graphrag tool function.

    Args:
        registry: GraphRAGToolRegistry instance

    Returns:
        Bound ask_graphrag tool function
    """
    @tool
    def bound_ask_graphrag(
        question: str,
        kg_id: str = "default",
        tenant_id: str = "default",
        agent_id: str = None,
        opts: Dict[str, Any] = None,
    ) -> Union[str, Dict[str, Any]]:
        return _ask_graphrag_impl(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            opts=opts,
            registry=registry,
        )

    return bound_ask_graphrag


def register_with_autogen(
    registry: GraphRAGToolRegistry,
    autogen_config: Dict[str, Any] = None
) -> Dict[str, Callable]:
    """Register GraphRAG tools with AutoGen Studio.

    Args:
        registry: GraphRAGToolRegistry instance
        autogen_config: Optional AutoGen configuration

    Returns:
        Dictionary of registered tool functions
    """
    # Create bound tool functions
    bound_ask_graphrag = create_ask_graphrag_tool(registry)

    # Include advanced tools
    from .advanced_graphrag_tools import create_bound_advanced_tools

    tools = {"ask_graphrag": bound_ask_graphrag}
    tools.update(create_bound_advanced_tools(registry))
    return tools