"""Neo4j GraphRAG port definitions for advanced knowledge graph capabilities."""

from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""

    OPENAI = "openai"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    HUGGINGFACE = "huggingface"


class RetrieverType(str, Enum):
    """Supported retriever types."""

    VECTOR = "vector"
    TEXT2CYPHER = "text2cypher"
    HYBRID = "hybrid"


class SimilarityFunction(str, Enum):
    """Supported vector similarity functions."""

    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"


@dataclass
class KGPipelineConfig:
    """Configuration for knowledge graph pipeline."""

    node_types: List[str]
    relationship_types: List[str]
    patterns: List[Dict[str, str]]  # Pattern definitions
    llm_config: Dict[str, Any]
    embedder_config: Dict[str, Any]
    from_pdf: bool = False
    chunk_size: int = 1000
    chunk_overlap: int = 200


@dataclass
class VectorIndexConfig:
    """Configuration for vector index."""

    index_name: str
    dimensions: int
    similarity_function: SimilarityFunction
    node_label: str = "Document"
    property_name: str = "embedding"


@dataclass
class RetrieverConfig:
    """Configuration for retrievers."""

    retriever_type: RetrieverType
    vector_index_name: Optional[str] = None
    top_k: int = 5
    similarity_threshold: float = 0.7
    cypher_examples: Optional[List[Dict[str, str]]] = None
    hybrid_weights: Optional[Dict[str, float]] = None


@dataclass
class SearchConfig:
    """Configuration for search operations."""

    top_k: int = 5
    similarity_threshold: float = 0.7
    include_metadata: bool = True
    filter_conditions: Optional[Dict[str, Any]] = None


@dataclass
class EntityExtractionConfig:
    """Configuration for entity extraction."""

    entity_types: List[str]
    relationship_types: List[str]
    extraction_patterns: List[Dict[str, str]]
    llm_model: str
    temperature: float = 0.1
    max_tokens: int = 2000


@dataclass
class GraphAnalyticsConfig:
    """Configuration for graph analytics."""

    algorithms: List[str]
    parameters: Dict[str, Any]
    node_filters: Optional[Dict[str, Any]] = None
    relationship_filters: Optional[Dict[str, Any]] = None


@dataclass
class KnowledgeGraphResult:
    """Result from knowledge graph construction."""

    pipeline_id: str
    node_count: int
    relationship_count: int
    processing_time_ms: float
    metadata: Dict[str, Any]


@dataclass
class RAGResponse:
    """Response from RAG search."""

    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    retrieval_time_ms: float
    generation_time_ms: float
    metadata: Dict[str, Any]


@dataclass
class VectorSearchResult:
    """Result from vector search."""

    node_id: str
    score: float
    content: str
    metadata: Dict[str, Any]


@dataclass
class EntityExtractionResult:
    """Result from entity extraction."""

    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    extraction_time_ms: float
    confidence_scores: Dict[str, float]


@dataclass
class GraphAnalyticsResult:
    """Result from graph analytics."""

    algorithm: str
    results: Dict[str, Any]
    processing_time_ms: float
    metadata: Dict[str, Any]


class Neo4jGraphRAGPort(Protocol):
    """Port for Neo4j GraphRAG operations."""

    @abstractmethod
    def create_kg_pipeline(self, *, config: KGPipelineConfig, tenant_id: str) -> str:
        """Create a knowledge graph construction pipeline.

        Args:
            config: Pipeline configuration
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Pipeline identifier

        Raises:
            Neo4jGraphRAGException: When pipeline creation fails
        """
        ...

    @abstractmethod
    def build_knowledge_graph(
        self, *, pipeline_id: str, documents: List[str], kg_id: str, tenant_id: str
    ) -> KnowledgeGraphResult:
        """Build knowledge graph from documents using pipeline.

        Args:
            pipeline_id: Pipeline identifier
            documents: List of document content
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Knowledge graph construction result

        Raises:
            Neo4jGraphRAGException: When graph construction fails
        """
        ...

    @abstractmethod
    def create_vector_index(self, *, config: VectorIndexConfig, tenant_id: str) -> bool:
        """Create vector index for embeddings.

        Args:
            config: Vector index configuration
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            True if index created successfully

        Raises:
            Neo4jGraphRAGException: When index creation fails
        """
        ...

    @abstractmethod
    def perform_vector_search(
        self, *, query: str, index_name: str, config: SearchConfig, tenant_id: str
    ) -> List[VectorSearchResult]:
        """Perform vector similarity search.

        Args:
            query: Search query
            index_name: Vector index name
            config: Search configuration
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            List of search results

        Raises:
            Neo4jGraphRAGException: When search fails
        """
        ...

    @abstractmethod
    def create_retriever(
        self, *, config: RetrieverConfig, kg_id: str, tenant_id: str
    ) -> str:
        """Create retriever for RAG operations.

        Args:
            config: Retriever configuration
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Retriever identifier

        Raises:
            Neo4jGraphRAGException: When retriever creation fails
        """
        ...

    @abstractmethod
    def perform_rag_search(
        self, *, retriever_id: str, query: str, config: SearchConfig, tenant_id: str
    ) -> RAGResponse:
        """Perform retrieval-augmented generation search.

        Args:
            retriever_id: Retriever identifier
            query: Search query
            config: Search configuration
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            RAG response with answer and sources

        Raises:
            Neo4jGraphRAGException: When RAG search fails
        """
        ...

    @abstractmethod
    def generate_embeddings(
        self,
        *,
        texts: List[str],
        provider: EmbeddingProvider,
        model_name: str,
        tenant_id: str,
    ) -> List[List[float]]:
        """Generate embeddings using specified provider.

        Args:
            texts: List of texts to embed
            provider: Embedding provider
            model_name: Model name for embedding
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            List of embedding vectors

        Raises:
            Neo4jGraphRAGException: When embedding generation fails
        """
        ...

    @abstractmethod
    def extract_entities_and_relationships(
        self, *, documents: List[str], config: EntityExtractionConfig, tenant_id: str
    ) -> EntityExtractionResult:
        """Extract entities and relationships from documents.

        Args:
            documents: List of document content
            config: Extraction configuration
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Extraction result with entities and relationships

        Raises:
            Neo4jGraphRAGException: When extraction fails
        """
        ...

    @abstractmethod
    def run_graph_analytics(
        self, *, kg_id: str, config: GraphAnalyticsConfig, tenant_id: str
    ) -> List[GraphAnalyticsResult]:
        """Run graph analytics algorithms.

        Args:
            kg_id: Knowledge graph identifier
            config: Analytics configuration
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            List of analytics results

        Raises:
            Neo4jGraphRAGException: When analytics fails
        """
        ...

    @abstractmethod
    def optimize_graph_queries(
        self, *, kg_id: str, queries: List[str], tenant_id: str
    ) -> Dict[str, Any]:
        """Optimize graph queries for performance.

        Args:
            kg_id: Knowledge graph identifier
            queries: List of queries to optimize
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Optimization results and recommendations

        Raises:
            Neo4jGraphRAGException: When optimization fails
        """
        ...

    @abstractmethod
    def get_pipeline_status(
        self, *, pipeline_id: str, tenant_id: str
    ) -> Dict[str, Any]:
        """Get status of a pipeline.

        Args:
            pipeline_id: Pipeline identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Pipeline status information

        Raises:
            Neo4jGraphRAGException: When status retrieval fails
        """
        ...

    @abstractmethod
    def delete_pipeline(self, *, pipeline_id: str, tenant_id: str) -> bool:
        """Delete a pipeline.

        Args:
            pipeline_id: Pipeline identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            True if pipeline deleted successfully

        Raises:
            Neo4jGraphRAGException: When deletion fails
        """
        ...
