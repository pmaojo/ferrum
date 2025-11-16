"""Application layer ports - Protocol interfaces for hexagonal architecture."""

from abc import abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, Iterator, List, Optional, Protocol, Tuple, Union

from domain.entities import (
    Community,
    DataRetentionTarget,
    GraphAccessPolicy,
    GraphBackup,
    GraphStreamEvent,
    Invoice,
    Job,
    Organization,
    Payment,
    SharingLink,
    Subscription,
    Triple,
    User,
    ValidationReport,
    Webhook,
    Workflow,
)


class GraphRetrieverPort(Protocol):
    """Port for GraphRAG document processing and knowledge graph querying.

    This port defines the contract for GraphRAG operations including document
    indexing for entity/relationship extraction and natural language querying
    against the knowledge graph.
    """

    @abstractmethod
    def index(self, *, docs: List[str], kg_id: str, tenant_id: str) -> List[Triple]:
        """Extract entities and relationships from documents using GraphRAG.

        Processes documents through GraphRAG indexing pipeline to extract
        structured knowledge in the form of subject-predicate-object triples.

        Args:
            docs: List of document content strings to process
            kg_id: Knowledge graph identifier for storage context
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            List of Triple objects representing extracted knowledge

        Raises:
            GraphRAGException: When document processing fails
            ValidationError: When extracted triples are malformed
        """
        ...

    @abstractmethod
    def run(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, List[Triple]]:
        """Execute natural language query against knowledge graph.

        Processes natural language questions using GraphRAG query engine
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

        Returns:
            Query results as formatted text or structured Triple list
            depending on opts.return_triples setting

        Raises:
            GraphRAGException: When query execution fails
            ValidationError: When query parameters are invalid
        """
        ...


class GraphTraversalPort(Protocol):
    """Port for executing Gremlin traversals over a graph database."""

    @abstractmethod
    def execute_traversal(self, traversal_query: str) -> List[Dict[str, Any]]:
        """Execute a Gremlin traversal and return the resulting records."""
        ...


class CodeOntologyPort(Protocol):
    """Port for extracting ontology triples from source code."""

    @abstractmethod
    def extract_triples(
        self, *, code: str, repo_id: str, tenant_id: str
    ) -> List[Triple]:
        """Parse code and emit ontology triples."""
        ...


class OntologyValidatorPort(Protocol):
    """Port for ontology validation with incremental reasoning capabilities.

    This port defines the contract for validating knowledge graph triples
    against ontological constraints using OWL reasoning, with support for
    delta validation and ontology versioning.
    """

    @abstractmethod
    def validate(
        self, *, triples: List[Triple], ontology_version_id: str
    ) -> ValidationReport:
        """Validate triples against ontological constraints with incremental reasoning.

        Performs comprehensive ontology validation using OWL reasoners to check
        consistency, identify unsatisfiable classes, and generate repair suggestions
        for constraint violations.

        Args:
            triples: List of Triple objects to validate
            ontology_version_id: Specific ontology version for validation context

        Returns:
            ValidationReport containing consistency status, unsatisfiable classes,
            and actionable repair suggestions

        Raises:
            ValidationError: When validation process fails
            OntologyException: When ontology version is not found
        """
        ...

    @abstractmethod
    def validate_delta(
        self, *, new_triples: List[Triple], existing_version_id: str, tenant_id: str
    ) -> ValidationReport:
        """Perform delta validation for ontology versioning and incremental updates.

        Validates only new triples against existing ontology version to enable
        efficient incremental reasoning without re-validating entire knowledge base.

        Args:
            new_triples: List of new Triple objects to validate incrementally
            existing_version_id: Parent ontology version for delta comparison
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            ValidationReport focused on delta changes with incremental consistency

        Raises:
            ValidationError: When delta validation fails
            VersioningException: When parent version is not found
        """
        ...

    @abstractmethod
    def convert_to_owl(self, *, triples: List[Triple]) -> str:
        """Convert triples to OWL axioms using Manchester syntax.

        Transforms knowledge graph triples into formal OWL axiom representation
        using Manchester syntax for ontology reasoning and validation.

        Args:
            triples: List of Triple objects to convert

        Returns:
            OWL axioms formatted in Manchester syntax as string

        Raises:
            ConversionError: When triple to OWL conversion fails
            SyntaxError: When Manchester syntax generation is invalid
        """
        ...


class QueryTranslatorPort(Protocol):
    """Port for natural language to graph query translation.

    This port defines the contract for converting natural language queries
    into structured graph queries (Cypher/GQL) with explanations.
    """

    @abstractmethod
    def translate(
        self, *, natural_language: str, kg_id: str, tenant_id: str
    ) -> Tuple[str, str]:
        """Convert natural language query to Cypher/GQL with explanation.

        Translates user's natural language questions into executable graph
        queries while providing human-readable explanations of the translation.

        Args:
            natural_language: User's natural language query
            kg_id: Knowledge graph identifier for context
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Tuple of (translated_query, explanation) where:
            - translated_query: Cypher/GQL query string
            - explanation: Human-readable translation explanation

        Raises:
            TranslationError: When query translation fails
            ValidationError: When natural language input is invalid
        """
        ...


class SparqlTranslatorPort(Protocol):
    """Port for translating natural language into SPARQL queries."""

    @abstractmethod
    def translate(
        self, *, natural_language: str, kg_id: str, tenant_id: str
    ) -> Tuple[str, str]:
        """Convert natural language query to SPARQL with explanation."""
        ...


class ShaclTranslatorPort(Protocol):
    """Port for translating natural language into SHACL shapes."""

    @abstractmethod
    def translate(
        self, *, natural_language: str, kg_id: str, tenant_id: str
    ) -> Tuple[str, str]:
        """Convert natural language constraints to SHACL with explanation."""
        ...


class GraphStreamPort(Protocol):
    """Port for real-time graph updates with batching and performance optimization.

    This port defines the contract for streaming graph events via WebSocket
    with buffering capabilities to handle high-volume updates efficiently.
    """

    @abstractmethod
    def send_event(self, *, event: GraphStreamEvent) -> None:
        """Send real-time graph update event via WebSocket.

        Streams individual graph events for real-time visualization updates
        with automatic buffering for performance optimization.

        Args:
            event: GraphStreamEvent containing update information

        Raises:
            StreamingError: When event transmission fails
            BufferOverflowError: When event buffer is full
        """
        ...

    @abstractmethod
    def send_batch(
        self, *, events: List[GraphStreamEvent], buffer_size: int = 1000
    ) -> None:
        """Send batched events to prevent WebSocket flooding for >10k events.

        Efficiently transmits large volumes of graph events in batches
        to prevent WebSocket connection overload and improve performance.

        Args:
            events: List of GraphStreamEvent objects to batch
            buffer_size: Maximum batch size for transmission optimization

        Raises:
            StreamingError: When batch transmission fails
            ValidationError: When buffer_size is invalid
        """
        ...


class MessageBusPort(Protocol):
    """Port for agent coordination with idempotency and multi-tenancy.

    This port defines the contract for message passing between agents
    with deduplication and tenant isolation capabilities.
    """

    @abstractmethod
    def publish(
        self,
        *,
        topic: str,
        message: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        tenant_id: str,
    ) -> None:
        """Publish message for agent coordination with deduplication.

        Publishes messages to specified topics with optional idempotency
        to prevent duplicate processing in multi-agent scenarios.

        Args:
            topic: Message topic for routing
            message: Message payload as dictionary
            idempotency_key: Optional key for duplicate prevention
            tenant_id: Tenant identifier for multi-tenant isolation

        Raises:
            PublishError: When message publishing fails
            ValidationError: When message format is invalid
        """
        ...

    @abstractmethod
    def subscribe(
        self, *, topic: str, handler: Callable[[Dict[str, Any]], None], tenant_id: str
    ) -> None:
        """Subscribe to messages with tenant isolation.

        Registers message handlers for specific topics with tenant-based
        filtering to ensure proper isolation in multi-tenant environments.

        Args:
            topic: Message topic to subscribe to
            handler: Callback function for message processing
            tenant_id: Tenant identifier for filtering messages

        Raises:
            SubscriptionError: When subscription setup fails
            ValidationError: When handler is invalid
        """
        ...


class TracingPort(Protocol):
    """Port for observability with OpenTelemetry integration.

    This port defines the contract for distributed tracing and metrics
    collection with tenant context for comprehensive system observability.
    """

    @abstractmethod
    def start_span(
        self, *, name: str, tenant_id: str, **kwargs: Any
    ) -> Any:  # OpenTelemetry Span type
        """Start OpenTelemetry span with tenant context.

        Creates distributed tracing spans for operation tracking with
        tenant context for multi-tenant observability.

        Args:
            name: Span name for operation identification
            tenant_id: Tenant identifier for context isolation
            **kwargs: Additional span attributes and metadata

        Returns:
            OpenTelemetry Span object for context management

        Raises:
            TracingError: When span creation fails
        """
        ...

    @abstractmethod
    def record_metric(
        self, *, name: str, value: float, tenant_id: str, **tags: Any
    ) -> None:
        """Record performance metrics with tenant isolation.

        Records system metrics (latency, throughput, error rates) with
        tenant context for comprehensive performance monitoring.

        Args:
            name: Metric name (e.g., 'graphrag_latency_ms')
            value: Metric value to record
            tenant_id: Tenant identifier for metric isolation
            **tags: Additional metric tags and dimensions

        Raises:
            MetricsError: When metric recording fails
        """
        ...


class ClusteringPort(Protocol):
    """Port for graph clustering and large graph visualization optimization.

    This port defines the contract for computing graph communities and
    managing progressive loading for large graph visualization.
    """

    @abstractmethod
    def compute_communities(
        self, *, kg_id: str, tenant_id: str, algorithm: str = "louvain"
    ) -> List[Community]:
        """Compute graph communities for large graph visualization using specified algorithm.

        Applies community detection algorithms (Louvain, etc.) to identify
        graph clusters for progressive rendering and visualization optimization.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            algorithm: Clustering algorithm name (default: "louvain")

        Returns:
            List of Community objects representing detected clusters

        Raises:
            ClusteringError: When community computation fails
            ValidationError: When algorithm is not supported
        """
        ...

    @abstractmethod
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
            ClusteringError: When subgraph retrieval fails
            ValidationError: When community_id is not found
        """
        ...


class GraphAnalyticsPort(Protocol):
    """Port for graph structure analysis and metrics calculation.

    This port defines the contract for analyzing graph structure,
    calculating various graph metrics, and providing insights.
    """

    @abstractmethod
    def analyze_structure(self, *, kg_id: str, tenant_id: str) -> Dict[str, float]:
        """Analyze graph structure and calculate metrics.

        Computes various graph structure metrics including density,
        clustering coefficient, diameter, and other topological measures.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Dictionary of metric names to values

        Raises:
            AnalyticsError: When structure analysis fails
            ValidationError: When graph is not found
        """
        ...

    @abstractmethod
    def calculate_centrality(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        centrality_types: List[str],
        node_ids: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, float]]:
        """Calculate centrality measures for nodes.

        Computes various centrality measures (betweenness, closeness,
        degree, eigenvector, pagerank) for specified nodes.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            centrality_types: List of centrality types to calculate
            node_ids: Optional list of specific nodes (None for all)

        Returns:
            Dictionary mapping node IDs to centrality measures

        Raises:
            AnalyticsError: When centrality calculation fails
            ValidationError: When parameters are invalid
        """
        ...

    @abstractmethod
    def find_shortest_path(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        source_node_id: str,
        target_node_id: str,
        max_depth: int = 10,
        weight_property: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Find shortest path between two nodes.

        Calculates the shortest path between source and target nodes
        using specified algorithm and optional edge weights.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            source_node_id: Source node identifier
            target_node_id: Target node identifier
            max_depth: Maximum search depth
            weight_property: Optional edge property for weights

        Returns:
            Path information dictionary or None if no path exists

        Raises:
            AnalyticsError: When path finding fails
            ValidationError: When nodes are not found
        """
        ...


class GraphRepositoryPort(Protocol):
    """Port for retrieving graph structure as triples."""

    @abstractmethod
    def get_triples(self, *, kg_id: str, tenant_id: str) -> List[Triple]:
        """Fetch all triples for the specified knowledge graph."""
        ...


class GraphVisualizationPort(Protocol):
    """Port for graph visualization and layout generation.

    This port defines the contract for generating graph visualizations
    with various layout algorithms and export capabilities.
    """

    @abstractmethod
    def generate_layout(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        algorithm: str = "force_directed",
        node_limit: int = 1000,
        include_communities: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate graph layout for visualization.

        Creates node positions and visual properties using specified
        layout algorithm with optional filtering and community detection.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            algorithm: Layout algorithm name
            node_limit: Maximum number of nodes to include
            include_communities: Whether to include community information
            filters: Optional filters for nodes and edges

        Returns:
            Layout data with node positions and visual properties

        Raises:
            VisualizationError: When layout generation fails
            ValidationError: When parameters are invalid
        """
        ...

    @abstractmethod
    def export_visualization(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        layout_data: Dict[str, Any],
        export_format: str,
        width: int = 1920,
        height: int = 1080,
        include_metadata: bool = True,
    ) -> Dict[str, Any]:
        """Export visualization to specified format.

        Converts layout data to various export formats including
        image formats (PNG, SVG) and graph formats (GraphML, GEXF).

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            layout_data: Layout data from generate_layout
            export_format: Target export format
            width: Image width for raster formats
            height: Image height for raster formats
            include_metadata: Whether to include metadata

        Returns:
            Export data with content and metadata

        Raises:
            VisualizationError: When export fails
            ValidationError: When format is not supported
        """
        ...


class VisualizationLayoutRepositoryPort(Protocol):
    """Port for retrieving stored visualization layouts."""

    @abstractmethod
    def get_layout(
        self,
        *,
        visualization_id: str,
        tenant_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve layout data by visualization identifier."""
        ...


class GraphExportPort(Protocol):
    """Port for exporting knowledge graphs in different formats.

    This port defines the contract for converting knowledge graphs into
    various standard formats like RDF, OWL, and JSON.
    """

    @abstractmethod
    def export_to_rdf(
        self, *, kg_id: str, tenant_id: str, format: str = "turtle"
    ) -> str:
        """Export knowledge graph to RDF format.

        Converts the knowledge graph triples into RDF serialization
        using the specified format (turtle, xml, n-triples, etc.).

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            format: RDF serialization format (turtle, xml, n-triples, json-ld)

        Returns:
            RDF serialized string in the requested format

        Raises:
            ExportError: When RDF export fails
            ValidationError: When format is not supported
        """
        ...

    @abstractmethod
    def export_to_owl(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        ontology_version_id: str,
        format: str = "manchester",
    ) -> str:
        """Export knowledge graph to OWL format with ontology.

        Converts the knowledge graph into OWL axioms using the specified
        ontology version for semantic context.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            ontology_version_id: Ontology version for semantic context
            format: OWL serialization format (manchester, xml, functional)

        Returns:
            OWL serialized string in the requested format

        Raises:
            ExportError: When OWL export fails
            ValidationError: When format is not supported
            OntologyException: When ontology version is not found
        """
        ...

    @abstractmethod
    def export_to_json(
        self, *, kg_id: str, tenant_id: str, include_metadata: bool = True
    ) -> str:
        """Export knowledge graph to JSON format.

        Converts the knowledge graph into a structured JSON representation
        with optional metadata inclusion.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            include_metadata: Whether to include graph metadata

        Returns:
            JSON serialized string representation of the graph

        Raises:
            ExportError: When JSON export fails
        """
        ...

    @abstractmethod
    def export_to_cypher(self, *, kg_id: str, tenant_id: str) -> str:
        """Export knowledge graph to Cypher query language.

        Converts the knowledge graph into a sequence of Cypher statements
        suitable for loading into Neo4j or other Cypher-compatible databases.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Cypher commands as a string

        Raises:
            ExportError: When Cypher export fails
        """
        ...


class LLMPort(Protocol):
    """Port for language model integration with streaming and tool support.

    This port defines the contract for interacting with large language models,
    providing a consistent interface for text generation with streaming capabilities
    and function calling support.
    """

    @abstractmethod
    def generate(
        self,
        *,
        prompt: str,
        tenant_id: str,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, Iterator[str]]:
        """Generate text from a prompt using the language model.

        Processes a text prompt through the language model to generate a response,
        with optional streaming and tool/function calling capabilities.

        Args:
            prompt: Text prompt to send to the language model
            tenant_id: Tenant identifier for multi-tenant isolation
            stream: Whether to stream the response tokens (default: False)
            tools: Optional list of tool definitions for function calling
            opts: Optional parameters including:
                - temperature: Sampling temperature (default: 0.7)
                - top_p: Nucleus sampling parameter (default: 0.95)
                - max_tokens: Maximum tokens to generate (default: 1024)
                - safety_settings: Model safety configuration

        Returns:
            Generated text as string or token iterator if streaming

        Raises:
            LLMException: When text generation fails
            QuotaExceededException: When API quota is exceeded
            ValidationError: When prompt or parameters are invalid
        """
        ...

    @abstractmethod
    def embed(
        self,
        *,
        text: Union[str, List[str]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for text using the language model.

        Creates vector embeddings for text input that can be used for
        semantic search, clustering, or other vector operations.

        Args:
            text: Text string or list of strings to embed
            tenant_id: Tenant identifier for multi-tenant isolation
            opts: Optional parameters for embedding generation

        Returns:
            Vector embedding(s) as list of floats or list of list of floats

        Raises:
            LLMException: When embedding generation fails
            QuotaExceededException: When API quota is exceeded
            ValidationError: When text input is invalid
        """
        ...

    @abstractmethod
    def moderate(
        self, *, text: str, tenant_id: str, opts: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Moderate content for safety and policy compliance.

        Analyzes text for harmful content, policy violations, or other safety concerns
        using the language model's content moderation capabilities.

        Args:
            text: Text content to moderate
            tenant_id: Tenant identifier for multi-tenant isolation
            opts: Optional parameters including:
                - categories: List of categories to check (default: all)
                - threshold: Minimum score to flag content (default: 0.7)

        Returns:
            Dictionary containing moderation results with categories and scores

        Raises:
            LLMException: When moderation fails
            QuotaExceededException: When API quota is exceeded
            ValidationError: When text input is invalid
        """
        ...

    @abstractmethod
    def get_token_count(self, *, text: str) -> int:
        """Calculate the number of tokens in the provided text.

        Estimates the token count for the given text according to the
        model's tokenization scheme.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count as integer

        Raises:
            ValidationError: When text input is invalid
        """
        ...


class AlertingPort(Protocol):
    """Port for emitting alerts to external systems."""

    @abstractmethod
    def send_alert(
        self, *, message: str, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send alert message with optional structured context."""
        ...


class MetricsRepositoryPort(Protocol):
    """Port for querying stored metrics from a time-series database."""

    @abstractmethod
    def query_range(
        self,
        *,
        metric: str,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
        labels: Optional[Dict[str, str]] = None,
    ) -> List[Tuple[datetime, float]]:
        """Retrieve metric data points for a specific metric and tenant."""
        ...


class VectorMathPort(Protocol):
    """Port for vector math operations used in context compression."""

    @abstractmethod
    def cosine_similarities(
        self,
        *,
        query_embedding: List[float],
        embeddings: List[List[float]],
    ) -> List[float]:
        """Calculate cosine similarities between query and embeddings."""
        ...


class ImageEmbeddingPort(Protocol):
    """Port for generating embeddings from images."""

    @abstractmethod
    def embed(
        self,
        *,
        images: Union[Any, List[Any]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for one or more images."""
        ...


class AudioEmbeddingPort(Protocol):
    """Port for generating embeddings from audio."""

    @abstractmethod
    def embed(
        self,
        *,
        audio: Union[Any, List[Any]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for one or more audio clips."""
        ...


class CachePort(Protocol):
    """Port for caching operations."""

    @abstractmethod
    def get(self, *, key: str, tenant_id: str) -> Optional[Any]:
        """Get a value from cache.

        Args:
            key: Cache key
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Cached value if found, None otherwise

        Raises:
            CacheError: When cache operation fails
        """
        ...

    @abstractmethod
    def set(
        self,
        *,
        key: str,
        value: Any,
        tenant_id: str,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            tenant_id: Tenant identifier for multi-tenant isolation
            ttl_seconds: Optional time-to-live in seconds

        Raises:
            CacheError: When cache operation fails
        """
        ...

    @abstractmethod
    def delete(self, *, key: str, tenant_id: str) -> bool:
        """Delete a value from cache.

        Args:
            key: Cache key
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            True if key was deleted, False if key was not found

        Raises:
            CacheError: When cache operation fails
        """
        ...

    @abstractmethod
    def exists(self, *, key: str, tenant_id: str) -> bool:
        """Check if a key exists in cache.

        Args:
            key: Cache key
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            True if key exists, False otherwise

        Raises:
            CacheError: When cache operation fails
        """
        ...

    @abstractmethod
    def clear(self, *, tenant_id: str) -> int:
        """Clear all cache entries for a tenant.

        Args:
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Number of keys deleted

        Raises:
            CacheError: When cache operation fails
        """
        ...




class UserRepositoryPort(Protocol):
    """Port for user repository operations."""

    @abstractmethod
    def create(self, user: User) -> User:
        """Create a new user.

        Args:
            user: User entity to create

        Returns:
            Created user entity

        Raises:
            RepositoryError: When creation fails
        """
        ...

    @abstractmethod
    def update(self, user: User) -> User:
        """Update an existing user.

        Args:
            user: User entity to update

        Returns:
            Updated user entity

        Raises:
            RepositoryError: When update fails
        """
        ...

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID.

        Args:
            user_id: User identifier

        Returns:
            User entity if found, None otherwise
        """
        ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address.

        Args:
            email: User email address

        Returns:
            User entity if found, None otherwise
        """
        ...

    @abstractmethod
    def list_by_organization(
        self, organization_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[User], int]:
        """List users in an organization with pagination.

        Args:
            organization_id: Organization identifier
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Tuple of (users list, total count)
        """
        ...

    @abstractmethod
    def delete_by_id(self, user_id: str) -> bool:
        """Delete user by ID.

        Args:
            user_id: User identifier

        Returns:
            True if deletion was successful, False otherwise

        Raises:
            RepositoryError: When deletion fails
        """
        ...


class OrganizationRepositoryPort(Protocol):
    """Port for organization repository operations."""

    @abstractmethod
    def create(self, organization: Organization) -> Organization:
        """Create a new organization.

        Args:
            organization: Organization entity to create

        Returns:
            Created organization entity

        Raises:
            RepositoryError: When creation fails
        """
        ...

    @abstractmethod
    def update(self, organization: Organization) -> Organization:
        """Update an existing organization.

        Args:
            organization: Organization entity to update

        Returns:
            Updated organization entity

        Raises:
            RepositoryError: When update fails
        """
        ...

    @abstractmethod
    def get_by_id(self, organization_id: str) -> Optional[Organization]:
        """Get organization by ID.

        Args:
            organization_id: Organization identifier

        Returns:
            Organization entity if found, None otherwise
        """
        ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Organization]:
        """Get organization by name.

        Args:
            name: Organization name

        Returns:
            Organization entity if found, None otherwise
        """
        ...


class SemanticSearchPort(Protocol):
    """Port for semantic search operations using embeddings."""

    @abstractmethod
    def search(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        query: str,
        limit: int = 20,
        threshold: float = 0.7,
        filter_by_node_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform semantic search using embeddings.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            query: Search query text
            limit: Maximum number of results
            threshold: Minimum similarity threshold
            filter_by_node_types: Optional node type filters

        Returns:
            List of search results with similarity scores

        Raises:
            SearchError: When search operation fails
        """
        ...


class EntitySearchPort(Protocol):
    """Port for entity search operations."""

    @abstractmethod
    def search_entities(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        entity_types: Optional[List[str]] = None,
        property_filters: Optional[Dict[str, Any]] = None,
        text_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: Optional[str] = None,
        sort_direction: str = "asc",
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Search for entities with filters and pagination.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            entity_types: Optional entity type filters
            property_filters: Optional property-based filters
            text_query: Optional text search query
            page: Page number for pagination
            page_size: Number of results per page
            sort_by: Optional field to sort by
            sort_direction: Sort direction (asc/desc)

        Returns:
            Tuple of (entities list, total count)

        Raises:
            SearchError: When search operation fails
        """
        ...


class RelationshipSearchPort(Protocol):
    """Port for relationship search operations."""

    @abstractmethod
    def search_relationships(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        source_node_id: Optional[str] = None,
        target_node_id: Optional[str] = None,
        relationship_types: Optional[List[str]] = None,
        pattern: Optional[str] = None,
        property_filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Search for relationships with pattern matching.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            source_node_id: Optional source node filter
            target_node_id: Optional target node filter
            relationship_types: Optional relationship type filters
            pattern: Optional Cypher-like pattern
            property_filters: Optional property-based filters
            page: Page number for pagination
            page_size: Number of results per page

        Returns:
            Tuple of (relationships list, total count)

        Raises:
            SearchError: When search operation fails
        """
        ...


class FacetedSearchPort(Protocol):
    """Port for faceted search operations."""

    @abstractmethod
    def search_with_facets(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        query: Optional[str] = None,
        selected_facets: Optional[Dict[str, List[str]]] = None,
        facet_fields: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Perform faceted search with aggregations.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            query: Optional search query
            selected_facets: Currently selected facet values
            facet_fields: Fields to generate facets for
            page: Page number for pagination
            page_size: Number of results per page

        Returns:
            Dictionary with search results and facet data

        Raises:
            SearchError: When search operation fails
        """
        ...


class SearchSuggestionsPort(Protocol):
    """Port for search suggestions and auto-completion."""

    @abstractmethod
    def get_suggestions(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        partial_query: str,
        suggestion_types: List[str],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get search suggestions for partial query.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            partial_query: Partial search query
            suggestion_types: Types of suggestions to return
            limit: Maximum number of suggestions

        Returns:
            List of suggestion objects with scores

        Raises:
            SearchError: When suggestion generation fails
        """
        ...


class SimilaritySearchPort(Protocol):
    """Port for entity similarity operations."""

    @abstractmethod
    def find_similar_entities(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        entity_id: str,
        similarity_algorithm: str = "embedding",
        limit: int = 10,
        threshold: float = 0.7,
        include_explanation: bool = True,
    ) -> List[Dict[str, Any]]:
        """Find entities similar to the given entity.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            entity_id: Source entity identifier
            similarity_algorithm: Algorithm to use for similarity
            limit: Maximum number of similar entities
            threshold: Minimum similarity threshold
            include_explanation: Whether to include similarity explanations

        Returns:
            List of similar entities with similarity scores

        Raises:
            SearchError: When similarity search fails
        """
        ...


class AuthorizationPort(Protocol):
    """Port for authorization and permission checking."""

    @abstractmethod
    def check_permission(self, user_id: str, resource_id: str, permission: str) -> bool:
        """Check if user has permission for resource.

        Args:
            user_id: User identifier
            resource_id: Resource identifier
            permission: Permission to check

        Returns:
            True if user has permission, False otherwise

        Raises:
            AuthorizationError: When permission check fails
        """
        ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Organization]:
        """Get organization by name.

        Args:
            name: Organization name

        Returns:
            Organization entity if found, None otherwise
        """
        ...

    @abstractmethod
    def list_organizations(
        self, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Organization], int]:
        """List organizations with pagination.

        Args:
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Tuple of (organizations list, total count)
        """
        ...

    @abstractmethod
    def delete_by_id(self, organization_id: str) -> bool:
        """Delete organization by ID.

        Args:
            organization_id: Organization identifier

        Returns:
            True if deletion was successful, False otherwise

        Raises:
            RepositoryError: When deletion fails
        """
        ...


class PasswordServicePort(Protocol):
    """Port for password hashing and validation operations."""

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash a password using secure hashing algorithm.

        Args:
            password: Plain text password to hash

        Returns:
            Hashed password string

        Raises:
            ValidationError: When password is invalid
        """
        ...

    @abstractmethod
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash.

        Args:
            password: Plain text password to verify
            password_hash: Hashed password to verify against

        Returns:
            True if password matches hash, False otherwise
        """
        ...


class AuthorizationServicePort(Protocol):
    """Port for authorization and permission checking operations."""

    @abstractmethod
    def check_permission(self, user_id: str, resource_id: str, action: str) -> None:
        """Check if user has permission to perform action on resource.

        Args:
            user_id: User identifier
            resource_id: Resource identifier
            action: Action to perform (e.g., "create", "read", "update", "delete")

        Raises:
            AuthorizationError: When user lacks permission
        """
        ...

    @abstractmethod
    def get_user_permissions(
        self, user_id: str, resource_id: Optional[str] = None
    ) -> List[str]:
        """Get list of permissions for a user.

        Args:
            user_id: User identifier
            resource_id: Optional specific resource identifier

        Returns:
            List of permission strings
        """
        ...

    @abstractmethod
    def get_graph_access_policy(
        self, *, kg_id: str, tenant_id: str, user_id: str
    ) -> Optional[GraphAccessPolicy]:
        """Retrieve access policy for a user and knowledge graph."""
        ...


class AuditServicePort(Protocol):
    """Port for audit logging operations."""

    @abstractmethod
    def log_activity(
        self,
        user_id: str,
        activity_type: str,
        description: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log user activity for audit trail.

        Args:
            user_id: User identifier
            activity_type: Type of activity (e.g., "user_created", "login")
            description: Human-readable description
            resource_id: Optional resource identifier
            resource_type: Optional resource type
            metadata: Optional additional metadata
        """
        ...

    @abstractmethod
    def get_user_activity(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        activity_types: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get user activity history.

        Args:
            user_id: Optional user identifier filter
            organization_id: Optional organization identifier filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            activity_types: Optional activity type filters
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Tuple of (activity records, total count)
        """
        ...




class SubscriptionRepositoryPort(Protocol):
    """Port for subscription repository operations."""

    @abstractmethod
    def create(self, subscription: Subscription) -> Subscription:
        """Create a new subscription.

        Args:
            subscription: Subscription entity to create

        Returns:
            Created subscription entity

        Raises:
            RepositoryError: When creation fails
        """
        ...

    @abstractmethod
    def update(self, subscription: Subscription) -> Subscription:
        """Update an existing subscription.

        Args:
            subscription: Subscription entity to update

        Returns:
            Updated subscription entity

        Raises:
            RepositoryError: When update fails
        """
        ...

    @abstractmethod
    def get_by_id(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by ID.

        Args:
            subscription_id: Subscription identifier

        Returns:
            Subscription entity if found, None otherwise
        """
        ...

    @abstractmethod
    def get_by_organization_id(self, organization_id: str) -> Optional[Subscription]:
        """Get active subscription by organization ID.

        Args:
            organization_id: Organization identifier

        Returns:
            Active subscription entity if found, None otherwise
        """
        ...

    @abstractmethod
    def list_by_organization(
        self, organization_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Subscription], int]:
        """List subscriptions for an organization with pagination.

        Args:
            organization_id: Organization identifier
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Tuple of (subscriptions list, total count)
        """
        ...

    @abstractmethod
    def delete_by_id(self, subscription_id: str) -> bool:
        """Delete subscription by ID.

        Args:
            subscription_id: Subscription identifier

        Returns:
            True if deletion was successful, False otherwise

        Raises:
            RepositoryError: When deletion fails
        """
        ...


class InvoiceRepositoryPort(Protocol):
    """Port for invoice repository operations."""

    @abstractmethod
    def create(self, invoice: Invoice) -> Invoice:
        """Create a new invoice.

        Args:
            invoice: Invoice entity to create

        Returns:
            Created invoice entity

        Raises:
            RepositoryError: When creation fails
        """
        ...

    @abstractmethod
    def update(self, invoice: Invoice) -> Invoice:
        """Update an existing invoice.

        Args:
            invoice: Invoice entity to update

        Returns:
            Updated invoice entity

        Raises:
            RepositoryError: When update fails
        """
        ...

    @abstractmethod
    def get_by_id(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID.

        Args:
            invoice_id: Invoice identifier

        Returns:
            Invoice entity if found, None otherwise
        """
        ...

    @abstractmethod
    def list_by_organization(
        self,
        organization_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Invoice], int]:
        """List invoices for an organization with pagination and date filtering.

        Args:
            organization_id: Organization identifier
            start_date: Optional start date filter
            end_date: Optional end date filter
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Tuple of (invoices list, total count)
        """
        ...

    @abstractmethod
    def list_by_subscription(
        self, subscription_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Invoice], int]:
        """List invoices for a subscription with pagination.

        Args:
            subscription_id: Subscription identifier
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Tuple of (invoices list, total count)
        """
        ...


class PaymentRepositoryPort(Protocol):
    """Port for payment repository operations."""

    @abstractmethod
    def create(self, payment: Payment) -> Payment:
        """Create a new payment.

        Args:
            payment: Payment entity to create

        Returns:
            Created payment entity

        Raises:
            RepositoryError: When creation fails
        """
        ...

    @abstractmethod
    def update(self, payment: Payment) -> Payment:
        """Update an existing payment.

        Args:
            payment: Payment entity to update

        Returns:
            Updated payment entity

        Raises:
            RepositoryError: When update fails
        """
        ...

    @abstractmethod
    def get_by_id(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID.

        Args:
            payment_id: Payment identifier

        Returns:
            Payment entity if found, None otherwise
        """
        ...

    @abstractmethod
    def list_by_invoice(self, invoice_id: str) -> List[Payment]:
        """List payments for an invoice.

        Args:
            invoice_id: Invoice identifier

        Returns:
            List of payment entities
        """
        ...

    @abstractmethod
    def list_by_organization(
        self,
        organization_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Payment], int]:
        """List payments for an organization with pagination and date filtering.

        Args:
            organization_id: Organization identifier
            start_date: Optional start date filter
            end_date: Optional end date filter
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
        Tuple of (payments list, total count)
        """
        ...


class WebhookRepositoryPort(Protocol):
    """Port for webhook repository operations."""

    @abstractmethod
    def create(self, webhook: Webhook) -> Webhook:
        """Create a new webhook."""
        ...

    @abstractmethod
    def update(self, webhook: Webhook) -> Webhook:
        """Update an existing webhook."""
        ...

    @abstractmethod
    def get_by_id(self, webhook_id: str) -> Optional[Webhook]:
        """Retrieve webhook by identifier."""
        ...

    @abstractmethod
    def list_by_tenant(
        self, tenant_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Webhook], int]:
        """List webhooks for a tenant."""
        ...

    @abstractmethod
    def delete_by_id(self, webhook_id: str) -> bool:
        """Delete webhook by ID."""
        ...


class SharingRepositoryPort(Protocol):
    """Port for knowledge graph sharing link operations."""

    @abstractmethod
    def create(self, link: SharingLink) -> SharingLink:
        """Create a new sharing link."""
        ...

    @abstractmethod
    def get_by_token(self, token: str, tenant_id: str) -> Optional[SharingLink]:
        """Retrieve a sharing link by token."""


class BackupRepositoryPort(Protocol):
    """Port for knowledge graph backup repository operations."""

    @abstractmethod
    def create(self, backup: GraphBackup) -> GraphBackup:
        """Persist a new backup entry."""
        ...

    @abstractmethod
    def get_by_id(self, backup_id: str) -> Optional[GraphBackup]:
        """Retrieve a backup by its identifier."""
        ...

    @abstractmethod
    def list_by_kg(
        self, kg_id: str, tenant_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[GraphBackup], int]:
        """List backups for a knowledge graph with pagination."""
        ...


class BackupStoragePort(Protocol):
    """Port for storage operations used during backups."""

    @abstractmethod
    def create_backup(self, *, kg_id: str, tenant_id: str) -> str:
        """Create a backup and return its storage location."""
        ...

    @abstractmethod
    def restore_backup(self, *, location: str, kg_id: str, tenant_id: str) -> None:
        """Restore a backup from the given location."""
        ...


class BillingAdapterPort(Protocol):
    """Port for external billing system integration."""

    @abstractmethod
    def create_subscription(
        self,
        organization_id: str,
        tier: str,
        billing_cycle: str,
        payment_method_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create subscription in external billing system.

        Args:
            organization_id: Organization identifier
            tier: Subscription tier
            billing_cycle: Billing cycle (monthly, yearly)
            payment_method_id: Payment method identifier

        Returns:
            Dictionary with external subscription details

        Raises:
            BillingError: When subscription creation fails
        """
        ...

    @abstractmethod
    def update_subscription(
        self,
        external_subscription_id: str,
        tier: Optional[str] = None,
        billing_cycle: Optional[str] = None,
        payment_method_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update subscription in external billing system.

        Args:
            external_subscription_id: External subscription identifier
            tier: Optional new subscription tier
            billing_cycle: Optional new billing cycle
            payment_method_id: Optional new payment method identifier

        Returns:
            Dictionary with updated subscription details

        Raises:
            BillingError: When subscription update fails
        """
        ...

    @abstractmethod
    def cancel_subscription(
        self, external_subscription_id: str, cancel_at_period_end: bool = True
    ) -> Dict[str, Any]:
        """Cancel subscription in external billing system.

        Args:
            external_subscription_id: External subscription identifier
            cancel_at_period_end: Whether to cancel at period end

        Returns:
            Dictionary with cancellation details

        Raises:
            BillingError: When subscription cancellation fails
        """
        ...

    @abstractmethod
    def get_usage_metrics(
        self,
        organization_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get usage metrics from external billing system.

        Args:
            organization_id: Organization identifier
            start_date: Optional start date for metrics
            end_date: Optional end date for metrics

        Returns:
            Dictionary with usage metrics

        Raises:
            BillingError: When metrics retrieval fails
        """
        ...


class SubscriptionServicePort(Protocol):
    """Port for subscription business logic operations."""

    @abstractmethod
    def check_subscription_limits(
        self,
        organization_id: str,
        resource_type: str,
        requested_amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Check subscription limits for a resource type.

        Args:
            organization_id: Organization identifier
            resource_type: Type of resource to check
            requested_amount: Optional amount being requested

        Returns:
            Dictionary with limit check results

        Raises:
            SubscriptionError: When limit check fails
        """
        ...

    @abstractmethod
    def get_subscription_limits(self, tier: str) -> Dict[str, Any]:
        """Get limits for a subscription tier.

        Args:
            tier: Subscription tier

        Returns:
            Dictionary with tier limits
        """
        ...

    @abstractmethod
    def calculate_proration(
        self, current_tier: str, new_tier: str, billing_cycle: str, days_remaining: int
    ) -> Dict[str, Any]:
        """Calculate proration for subscription changes.

        Args:
            current_tier: Current subscription tier
            new_tier: New subscription tier
            billing_cycle: Billing cycle
            days_remaining: Days remaining in current period

        Returns:
            Dictionary with proration details
        """
        ...


class DataRetentionServicePort(Protocol):
    """Port for enforcing tenant data retention policies."""

    @abstractmethod
    def delete_expired_data(
        self,
        *,
        tenant_id: str,
        applies_to: DataRetentionTarget,
        older_than: datetime,
    ) -> int:
        """Delete data older than the specified datetime."""
        ...


class WorkflowOrchestratorPort(Protocol):
    """Port for orchestrating workflows across frameworks."""

    @abstractmethod
    def register_workflow(
        self,
        *,
        workflow_id: str,
        steps: List[Dict[str, Any]],
        framework: str,
        tenant_id: str,
    ) -> None:
        """Register a workflow configuration."""
        ...

    @abstractmethod
    def execute_workflow(
        self, *, workflow_id: str, input_data: Dict[str, Any], tenant_id: str
    ) -> Dict[str, Any]:
        """Execute a registered workflow."""
        ...

    @abstractmethod
    def execute_with_fallback(
        self,
        *,
        workflow_id: str,
        input_data: Dict[str, Any],
        tenant_id: str,
        fallback_workflow_id: str,
        max_retries: int,
        retry_delay_seconds: int,
    ) -> Dict[str, Any]:
        """Execute a workflow with fallback."""
        ...

    @abstractmethod
    def execute_parallel_workflows(
        self,
        *,
        workflow_configs: List[Dict[str, Any]],
        tenant_id: str,
        timeout_seconds: int,
        aggregate_results: bool,
    ) -> Dict[str, Any]:
        """Execute multiple workflows in parallel."""
        ...

    @abstractmethod
    def register_workflow_template(
        self,
        *,
        template_id: str,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        tenant_id: str,
    ) -> str:
        """Register a workflow template."""
        ...

    @abstractmethod
    def instantiate_workflow(
        self,
        *,
        template_id: str,
        workflow_id: Optional[str],
        parameters: Dict[str, Any],
        tenant_id: Optional[str],
    ) -> str:
        """Instantiate a workflow from a template."""
        ...

    @abstractmethod
    def create_workflow_monitor(
        self,
        *,
        workflow_id: str,
        check_interval_seconds: int,
        timeout_seconds: int,
    ) -> Dict[str, Any]:
        """Create a monitoring task for a workflow."""
        ...

    @abstractmethod
    def get_workflow_status(
        self, *, workflow_id: str, include_history: bool = False
    ) -> Dict[str, Any]:
        """Retrieve workflow execution status."""
        ...


class FlowiseAdapterPort(Protocol):
    """Port for Flowise adapter interactions."""

    @abstractmethod
    def query_knowledge_graph(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query the knowledge graph using natural language."""
        ...

    @abstractmethod
    def index_documents(
        self,
        *,
        docs: List[str],
        kg_id: str,
        tenant_id: str,
        validate: bool = True,
        ontology_version_id: str = "latest",
    ) -> Dict[str, Any]:
        """Index documents into the knowledge graph."""
        ...

    @abstractmethod
    def create_workflow(
        self,
        *,
        workflow_id: str,
        steps: List[Dict[str, Any]],
        tenant_id: str,
    ) -> str:
        """Create a new workflow."""
        ...

    @abstractmethod
    def execute_workflow(
        self,
        *,
        workflow_id: str,
        input_data: Dict[str, Any],
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Execute a workflow."""
        ...

    @abstractmethod
    def orchestrator(self) -> WorkflowOrchestratorPort:
        """Return orchestrator for advanced operations."""
        ...


class WorkflowRepositoryPort(Protocol):
    """Port for workflow repository operations."""

    @abstractmethod
    def create(self, workflow: Workflow) -> Workflow:
        """Create a new workflow.

        Args:
            workflow: Workflow entity to create

        Returns:
            Created workflow entity

        Raises:
            RepositoryError: When creation fails
        """
        ...

    @abstractmethod
    def update(self, workflow: Workflow) -> Workflow:
        """Update an existing workflow.

        Args:
            workflow: Workflow entity to update

        Returns:
            Updated workflow entity

        Raises:
            RepositoryError: When update fails
        """
        ...

    @abstractmethod
    def get_by_id(self, workflow_id: str, tenant_id: str) -> Optional[Workflow]:
        """Get workflow by ID.

        Args:
            workflow_id: Workflow identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Workflow entity if found, None otherwise
        """
        ...

    @abstractmethod
    def list_by_tenant(
        self,
        tenant_id: str,
        workflow_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Workflow], int]:
        """List workflows for a tenant with pagination.

        Args:
            tenant_id: Tenant identifier
            workflow_type: Optional workflow type filter
            is_active: Optional active status filter
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Tuple of (workflows list, total count)
        """
        ...

    @abstractmethod
    def delete(self, workflow_id: str, tenant_id: str) -> bool:
        """Delete a workflow.

        Args:
            workflow_id: Workflow identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            True if deleted, False if not found
        """
        ...


class JobRepositoryPort(Protocol):
    """Port for job repository operations."""

    @abstractmethod
    def create(self, job: Job) -> Job:
        """Create a new job.

        Args:
            job: Job entity to create

        Returns:
            Created job entity

        Raises:
            RepositoryError: When creation fails
        """
        ...

    @abstractmethod
    def update(self, job: Job) -> Job:
        """Update an existing job.

        Args:
            job: Job entity to update

        Returns:
            Updated job entity

        Raises:
            RepositoryError: When update fails
        """
        ...

    @abstractmethod
    def get_by_id(self, job_id: str, tenant_id: str) -> Optional[Job]:
        """Get job by ID.

        Args:
            job_id: Job identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Job entity if found, None otherwise
        """
        ...

    @abstractmethod
    def list_by_tenant(
        self,
        tenant_id: str,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        created_by: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Job], int]:
        """List jobs for a tenant with pagination and filtering.

        Args:
            tenant_id: Tenant identifier
            workflow_id: Optional workflow ID filter
            status: Optional job status filter
            created_by: Optional creator filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Tuple of (jobs list, total count)
        """
        ...

    @abstractmethod
    def list_by_workflow(
        self,
        workflow_id: str,
        tenant_id: str,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Job], int]:
        """List jobs for a specific workflow with pagination.

        Args:
            workflow_id: Workflow identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            status: Optional job status filter
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Tuple of (jobs list, total count)
        """
        ...

    @abstractmethod
    def delete(self, job_id: str, tenant_id: str) -> bool:
        """Delete a job.

        Args:
            job_id: Job identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            True if deleted, False if not found
        """
        ...


class WorkflowExecutionPort(Protocol):
    """Port for workflow execution operations."""

    @abstractmethod
    def execute_workflow(
        self,
        workflow: Workflow,
        input_parameters: Dict[str, Any],
        job_id: str,
    ) -> Dict[str, Any]:
        """Execute a workflow asynchronously.

        Args:
            workflow: Workflow entity to execute
            input_parameters: Input parameters for execution
            job_id: Job identifier for tracking

        Returns:
            Execution result data

        Raises:
            WorkflowExecutionError: When execution fails
        """
        ...

    @abstractmethod
    def cancel_job(self, job_id: str, tenant_id: str) -> bool:
        """Cancel a running job.

        Args:
            job_id: Job identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            True if cancelled, False if not found or not cancellable
        """
        ...

    @abstractmethod
    def get_job_progress(self, job_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get current job progress information.

        Args:
            job_id: Job identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Progress information dictionary or None if not found
        """
        ...


class WorkflowValidationPort(Protocol):
    """Port for workflow validation operations."""

    @abstractmethod
    def validate_workflow_definition(
        self, definition: Dict[str, Any], workflow_type: str
    ) -> Tuple[bool, List[str]]:
        """Validate workflow definition.

        Args:
            definition: Workflow definition to validate
            workflow_type: Type of workflow

        Returns:
            Tuple of (is_valid, error_messages)
        """
        ...

    @abstractmethod
    def validate_input_parameters(
        self, workflow: Workflow, input_parameters: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate input parameters for a workflow.

        Args:
            workflow: Workflow entity
            input_parameters: Input parameters to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        ...


class WebhookServicePort(Protocol):
    """Port for webhook HTTP operations."""

    @abstractmethod
    def send_test_event(
        self,
        *,
        url: str,
        secret: str,
        event_type: str,
        payload: Dict[str, Any],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Send a test event to a webhook URL.

        Args:
            url: Webhook URL to send the event to
            secret: Webhook secret for signature generation
            event_type: Type of event being sent
            payload: Event payload data
            timeout: Request timeout in seconds

        Returns:
            Dictionary containing response information:
            - success: bool
            - status_code: int
            - response_time_ms: float
            - error_message: Optional[str]

        Raises:
            WebhookError: When webhook request fails
        """
        ...

    @abstractmethod
    def validate_webhook_url(self, *, url: str, timeout: int = 10) -> Dict[str, Any]:
        """Validate that a webhook URL is reachable.

        Args:
            url: Webhook URL to validate
            timeout: Request timeout in seconds

        Returns:
            Dictionary containing validation result:
            - is_valid: bool
            - status_code: Optional[int]
            - error_message: Optional[str]

        Raises:
            ValidationError: When URL validation fails
        """
        ...


class ExternalDataSyncPort(Protocol):
    """Port for synchronizing data from external systems."""

    @abstractmethod
    def sync_from_source(
        self,
        *,
        source_type: str,
        source_config: Dict[str, Any],
        target_kg_id: str,
        tenant_id: str,
        sync_mode: str = "incremental",
        transformation_rules: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Synchronize data from an external source.

        Args:
            source_type: Type of external source (api, database, file)
            source_config: Configuration for the external source
            target_kg_id: Target knowledge graph ID
            tenant_id: Tenant identifier
            sync_mode: Synchronization mode (full, incremental, delta)
            transformation_rules: Optional data transformation rules

        Returns:
            Dictionary containing sync results:
            - sync_id: str
            - status: str
            - records_processed: int
            - records_imported: int
            - records_failed: int
            - error_message: Optional[str]

        Raises:
            SyncError: When synchronization fails
        """
        ...


class ExternalDataExportPort(Protocol):
    """Port for exporting data to external systems."""

    @abstractmethod
    def export_to_target(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        target_type: str,
        target_config: Dict[str, Any],
        export_format: str = "json",
        export_filters: Optional[Dict[str, Any]] = None,
        transformation_rules: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Export data to an external target.

        Args:
            kg_id: Source knowledge graph ID
            tenant_id: Tenant identifier
            target_type: Type of external target (api, database, file)
            target_config: Configuration for the external target
            export_format: Export format (json, rdf, csv, xml)
            export_filters: Optional filters for data export
            transformation_rules: Optional data transformation rules

        Returns:
            Dictionary containing export results:
            - export_id: str
            - status: str
            - records_exported: int
            - records_failed: int
            - export_location: Optional[str]
            - error_message: Optional[str]

        Raises:
            ExportError: When export fails
        """
        ...


class IntegrationStatusPort(Protocol):
    """Port for checking integration status."""

    @abstractmethod
    def check_integration_status(
        self,
        *,
        tenant_id: str,
        integration_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Check the status of integrations for a tenant.

        Args:
            tenant_id: Tenant identifier
            integration_type: Optional filter by integration type

        Returns:
            List of integration status dictionaries:
            - integration_type: str
            - integration_id: str
            - name: str
            - status: str (active, inactive, error, pending)
            - last_check_at: Optional[datetime]
            - error_message: Optional[str]
            - metadata: Dict[str, Any]

        Raises:
            IntegrationError: When status check fails
        """
        ...
