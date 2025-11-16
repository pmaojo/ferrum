"""Semantic embedding cache adapter using Redis + HNSW.

This adapter implements a semantic embedding cache for Gemini Text-Embedding-4
vectors using Redis with HNSW (Hierarchical Navigable Small World) for efficient
vector similarity search with tenant isolation.
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import redis
from redis.commands.search.field import TextField, VectorField

try:
    from redis.commands.search.indexDefinition import IndexDefinition, IndexType
except ImportError:
    try:
        from redis.commands.search import IndexDefinition, IndexType
    except ImportError:
        # Fallback for older redis versions
        IndexDefinition = None
        IndexType = None

from domain.services import GraphRAGException

# Configure logging
logger = logging.getLogger(__name__)


class EmbeddingCacheException(GraphRAGException):
    """Exception for embedding cache operations."""

    def __init__(self, message: str, error_code: str, context: Dict[str, Any]):
        super().__init__(message=message, error_code=error_code, context=context)


class EmbeddingCacheAdapter:
    """Adapter for caching embeddings using Redis + HNSW with tenant isolation.

    Implements a semantic embedding cache for Gemini Text-Embedding-4 vectors
    using Redis with HNSW (Hierarchical Navigable Small World) for efficient
    vector similarity search with tenant isolation.
    """

    def __init__(
        self,
        redis_url: str,
        index_name: str = "embedding_cache",
        vector_dim: int = 768,  # Gemini Text-Embedding-4 dimension
        distance_metric: str = "COSINE",
        index_type: str = "HNSW",
        cache_ttl: int = 86400 * 30,  # 30 days default TTL
        tracer=None,
    ):
        """Initialize EmbeddingCacheAdapter with Redis connection and configuration.

        Args:
            redis_url: Redis connection URL
            index_name: Name of the Redis search index
            vector_dim: Dimension of embedding vectors
            distance_metric: Distance metric for vector similarity (COSINE, L2, IP)
            index_type: Index type for vector search (HNSW, FLAT)
            cache_ttl: Time-to-live for cached embeddings in seconds
            tracer: Optional tracing port for observability

        Raises:
            EmbeddingCacheException: When Redis connection or index creation fails
        """
        self.redis_url = redis_url
        self.index_name = index_name
        self.vector_dim = vector_dim
        self.distance_metric = distance_metric
        self.index_type = index_type
        self.cache_ttl = cache_ttl
        self.tracer = tracer

        try:
            # Initialize Redis client
            self.redis_client = redis.from_url(redis_url)

            # Verify connection
            self.redis_client.ping()

            # Create vector search index if it doesn't exist
            self._create_index()

            logger.info(
                f"Initialized EmbeddingCacheAdapter with Redis at {redis_url}, "
                f"index={index_name}, dim={vector_dim}, metric={distance_metric}"
            )

        except redis.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}", exc_info=True)
            raise EmbeddingCacheException(
                message=f"Failed to connect to Redis: {str(e)}",
                error_code="REDIS_CONNECTION_ERROR",
                context={"redis_url": redis_url},
            ) from e
        except Exception as e:
            logger.error(
                f"Failed to initialize embedding cache: {str(e)}", exc_info=True
            )
            raise EmbeddingCacheException(
                message=f"Failed to initialize embedding cache: {str(e)}",
                error_code="EMBEDDING_CACHE_INIT_ERROR",
                context={"redis_url": redis_url, "index_name": index_name},
            ) from e

    def get_embedding(
        self,
        *,
        text: Union[str, List[str]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Optional[Union[List[float], List[List[float]]]]:
        """Get cached embedding for text if available.

        Retrieves cached embedding vectors for text input with tenant isolation,
        using hash-based lookup to avoid recalculation for identical inputs.

        Args:
            text: Text string or list of strings to get embeddings for
            tenant_id: Tenant identifier for multi-tenant isolation
            opts: Optional parameters affecting embedding generation

        Returns:
            Cached vector embedding(s) if found, None otherwise

        Raises:
            EmbeddingCacheException: When cache retrieval fails
        """
        start_time = datetime.now()

        try:
            # Generate hash for cache key
            text_hash = self._generate_hash(text, tenant_id, opts)
            cache_key = f"{tenant_id}:embedding:{text_hash}"

            # Check if embedding exists in cache
            if not self.redis_client.exists(cache_key):
                logger.debug(f"Cache miss for {cache_key}")
                return None

            # Retrieve cached embedding
            cached_data = self.redis_client.hgetall(cache_key)

            if not cached_data or b"vector" not in cached_data:
                logger.warning(f"Invalid cache entry for {cache_key}")
                return None

            # Parse vector data
            vector_data = json.loads(cached_data[b"vector"].decode())

            # Record metrics
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            if self.tracer:
                self.tracer.record_metric(
                    name="embedding_cache_hit_latency_ms",
                    value=execution_time_ms,
                    tenant_id=tenant_id,
                )
                self.tracer.record_metric(
                    name="embedding_cache_hit_count", value=1.0, tenant_id=tenant_id
                )

            logger.debug(f"Cache hit for {cache_key} in {execution_time_ms:.2f}ms")
            return vector_data

        except Exception as e:
            logger.error(
                f"Failed to retrieve cached embedding: {str(e)}", exc_info=True
            )

            # Record error metric
            if self.tracer:
                self.tracer.record_metric(
                    name="embedding_cache_error_count",
                    value=1.0,
                    tenant_id=tenant_id,
                    error_type=type(e).__name__,
                )

            # Return None on error to allow fallback to direct embedding generation
            return None

    def store_embedding(
        self,
        *,
        text: Union[str, List[str]],
        embedding: Union[List[float], List[List[float]]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """Store embedding in cache with tenant isolation.

        Caches embedding vectors for text input with tenant isolation and TTL,
        using hash-based keys to enable efficient lookup and avoid recalculation.

        Args:
            text: Text string or list of strings that was embedded
            embedding: Vector embedding(s) to cache
            tenant_id: Tenant identifier for multi-tenant isolation
            opts: Optional parameters that affected embedding generation
            ttl: Optional custom TTL in seconds (defaults to self.cache_ttl)

        Returns:
            True if embedding was successfully cached, False otherwise

        Raises:
            EmbeddingCacheException: When cache storage fails
        """
        start_time = datetime.now()

        try:
            # Generate hash for cache key
            text_hash = self._generate_hash(text, tenant_id, opts)
            cache_key = f"{tenant_id}:embedding:{text_hash}"

            # Prepare metadata
            metadata = {
                "tenant_id": tenant_id,
                "created_at": datetime.now().isoformat(),
                "text_type": "batch" if isinstance(text, list) else "single",
                "vector_dim": self.vector_dim,
                "hash": text_hash,
            }

            # Add text sample for debugging (truncated for large inputs)
            if isinstance(text, str):
                metadata["text_sample"] = text[:100] + (
                    "..." if len(text) > 100 else ""
                )
                metadata["text_count"] = len(text)
            else:
                metadata["text_count"] = len(text)
                if text:
                    metadata["text_sample"] = text[0][:100] + (
                        "..." if len(text[0]) > 100 else ""
                    )

            # Add options to metadata if provided
            if opts:
                metadata["opts"] = json.dumps(opts)

            # Store embedding and metadata
            pipeline = self.redis_client.pipeline()

            # Store as hash with vector and metadata fields
            pipeline.hset(
                cache_key,
                mapping={
                    "vector": json.dumps(embedding),
                    "metadata": json.dumps(metadata),
                    "tenant_id": tenant_id,
                    "created_at": int(time.time()),
                },
            )

            # Set TTL
            effective_ttl = ttl if ttl is not None else self.cache_ttl
            if effective_ttl > 0:
                pipeline.expire(cache_key, effective_ttl)

            # Add to tenant index for management
            tenant_index_key = f"{tenant_id}:embeddings"
            pipeline.sadd(tenant_index_key, cache_key)

            # Execute pipeline
            pipeline.execute()

            # Record metrics
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            if self.tracer:
                self.tracer.record_metric(
                    name="embedding_cache_store_latency_ms",
                    value=execution_time_ms,
                    tenant_id=tenant_id,
                )
                self.tracer.record_metric(
                    name="embedding_cache_store_count", value=1.0, tenant_id=tenant_id
                )

            logger.debug(
                f"Cached embedding for {cache_key} in {execution_time_ms:.2f}ms "
                f"with TTL={effective_ttl}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to cache embedding: {str(e)}", exc_info=True)

            # Record error metric
            if self.tracer:
                self.tracer.record_metric(
                    name="embedding_cache_error_count",
                    value=1.0,
                    tenant_id=tenant_id,
                    error_type=type(e).__name__,
                )

            return False

    def find_similar(
        self,
        *,
        embedding: List[float],
        tenant_id: str,
        top_k: int = 5,
        score_threshold: float = 0.75,
    ) -> List[Dict[str, Any]]:
        """Find similar embeddings using vector similarity search.

        Performs vector similarity search using HNSW index to find
        semantically similar content based on embedding vectors.

        Args:
            embedding: Query vector embedding
            tenant_id: Tenant identifier for multi-tenant isolation
            top_k: Maximum number of results to return
            score_threshold: Minimum similarity score threshold (0-1)

        Returns:
            List of similar items with metadata and similarity scores

        Raises:
            EmbeddingCacheException: When similarity search fails
        """
        start_time = datetime.now()

        try:
            # Prepare query with tenant filter
            query = f"@tenant_id:{{{tenant_id}}}"

            # Execute vector search
            results = self.redis_client.ft(self.index_name).search(
                query,
                query_params={"vec_param": embedding, "tenant_id": tenant_id},
                return_fields=["vector", "metadata", "tenant_id", "created_at"],
                scorer="VECTOR_SCORE",
                num=top_k,
            )

            # Process results
            similar_items = []
            for doc in results.docs:
                # Convert distance to similarity score (1 - distance)
                score = 1 - float(doc.vector_score)

                if score < score_threshold:
                    continue

                # Parse metadata
                metadata = json.loads(doc.metadata) if hasattr(doc, "metadata") else {}

                # Add to results
                similar_items.append(
                    {
                        "key": doc.id,
                        "score": score,
                        "metadata": metadata,
                        "created_at": (
                            datetime.fromtimestamp(int(doc.created_at))
                            if hasattr(doc, "created_at")
                            else None
                        ),
                    }
                )

            # Record metrics
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            if self.tracer:
                self.tracer.record_metric(
                    name="embedding_similarity_search_latency_ms",
                    value=execution_time_ms,
                    tenant_id=tenant_id,
                )
                self.tracer.record_metric(
                    name="embedding_similarity_search_count",
                    value=1.0,
                    tenant_id=tenant_id,
                )
                self.tracer.record_metric(
                    name="embedding_similarity_result_count",
                    value=len(similar_items),
                    tenant_id=tenant_id,
                )

            logger.debug(
                f"Found {len(similar_items)} similar items for tenant {tenant_id} "
                f"in {execution_time_ms:.2f}ms"
            )
            return similar_items

        except Exception as e:
            logger.error(f"Similarity search failed: {str(e)}", exc_info=True)

            # Record error metric
            if self.tracer:
                self.tracer.record_metric(
                    name="embedding_cache_error_count",
                    value=1.0,
                    tenant_id=tenant_id,
                    error_type=type(e).__name__,
                )

            raise EmbeddingCacheException(
                message=f"Similarity search failed: {str(e)}",
                error_code="EMBEDDING_SIMILARITY_SEARCH_ERROR",
                context={"tenant_id": tenant_id, "top_k": top_k},
            ) from e

    def get_tenant_stats(self, *, tenant_id: str) -> Dict[str, Any]:
        """Get cache statistics for a tenant.

        Retrieves cache usage statistics for a specific tenant,
        including embedding count, storage size, and age distribution.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dictionary of cache statistics

        Raises:
            EmbeddingCacheException: When stats retrieval fails
        """
        try:
            # Get tenant's embedding keys
            tenant_index_key = f"{tenant_id}:embeddings"
            embedding_keys = self.redis_client.smembers(tenant_index_key)

            # Initialize stats
            stats = {
                "embedding_count": len(embedding_keys),
                "total_size_bytes": 0,
                "age_distribution": {
                    "last_hour": 0,
                    "last_day": 0,
                    "last_week": 0,
                    "older": 0,
                },
            }

            # Current time for age calculation
            now = datetime.now()

            # Process each embedding
            for key in embedding_keys:
                # Skip if key doesn't exist (expired)
                if not self.redis_client.exists(key):
                    continue

                # Get metadata
                created_at = self.redis_client.hget(key, "created_at")
                if created_at:
                    created_timestamp = int(created_at)
                    created_date = datetime.fromtimestamp(created_timestamp)
                    age = now - created_date

                    # Update age distribution
                    if age < timedelta(hours=1):
                        stats["age_distribution"]["last_hour"] += 1
                    elif age < timedelta(days=1):
                        stats["age_distribution"]["last_day"] += 1
                    elif age < timedelta(weeks=1):
                        stats["age_distribution"]["last_week"] += 1
                    else:
                        stats["age_distribution"]["older"] += 1

                # Get memory usage
                size = self.redis_client.memory_usage(key)
                if size:
                    stats["total_size_bytes"] += size

            # Add average size
            if stats["embedding_count"] > 0:
                stats["avg_size_bytes"] = (
                    stats["total_size_bytes"] / stats["embedding_count"]
                )
            else:
                stats["avg_size_bytes"] = 0

            return stats

        except Exception as e:
            logger.error(f"Failed to get tenant stats: {str(e)}", exc_info=True)
            raise EmbeddingCacheException(
                message=f"Failed to get tenant stats: {str(e)}",
                error_code="EMBEDDING_CACHE_STATS_ERROR",
                context={"tenant_id": tenant_id},
            ) from e

    def clear_tenant_cache(
        self, *, tenant_id: str, older_than_days: Optional[int] = None
    ) -> int:
        """Clear cached embeddings for a tenant.

        Removes cached embeddings for a specific tenant with optional
        age filtering to clear only older entries.

        Args:
            tenant_id: Tenant identifier
            older_than_days: Optional age filter in days

        Returns:
            Number of cache entries cleared

        Raises:
            EmbeddingCacheException: When cache clearing fails
        """
        try:
            # Get tenant's embedding keys
            tenant_index_key = f"{tenant_id}:embeddings"
            embedding_keys = self.redis_client.smembers(tenant_index_key)

            # Initialize counter
            cleared_count = 0

            # Current time for age calculation
            now = int(time.time())
            age_threshold = now - (older_than_days * 86400) if older_than_days else 0

            # Process each embedding
            pipeline = self.redis_client.pipeline()
            for key in embedding_keys:
                # Skip if key doesn't exist (already expired)
                if not self.redis_client.exists(key):
                    pipeline.srem(tenant_index_key, key)
                    continue

                # Check age if filter is applied
                if older_than_days:
                    created_at = self.redis_client.hget(key, "created_at")
                    if created_at and int(created_at) > age_threshold:
                        continue  # Skip if not old enough

                # Delete the key
                pipeline.delete(key)
                pipeline.srem(tenant_index_key, key)
                cleared_count += 1

            # Execute pipeline
            pipeline.execute()

            logger.info(
                f"Cleared {cleared_count} cache entries for tenant {tenant_id}"
                + (f" older than {older_than_days} days" if older_than_days else "")
            )
            return cleared_count

        except Exception as e:
            logger.error(f"Failed to clear tenant cache: {str(e)}", exc_info=True)
            raise EmbeddingCacheException(
                message=f"Failed to clear tenant cache: {str(e)}",
                error_code="EMBEDDING_CACHE_CLEAR_ERROR",
                context={"tenant_id": tenant_id, "older_than_days": older_than_days},
            ) from e

    def _create_index(self) -> None:
        """Create vector search index if it doesn't exist.

        Creates a Redis search index with vector field for HNSW similarity search
        and additional fields for filtering and metadata.

        Raises:
            EmbeddingCacheException: When index creation fails
        """
        try:
            # Check if index already exists
            try:
                self.redis_client.ft(self.index_name).info()
                logger.debug(f"Index {self.index_name} already exists")
                return
            except Exception:
                # Index doesn't exist, create it
                pass

            # Define schema fields
            schema = [
                # Vector field for embeddings
                VectorField(
                    "vector",
                    self.index_type,
                    {
                        "TYPE": "FLOAT32",
                        "DIM": self.vector_dim,
                        "DISTANCE_METRIC": self.distance_metric,
                        "INITIAL_CAP": 1000,
                        "M": 40,  # HNSW parameter: max outgoing edges per node
                        "EF_CONSTRUCTION": 200,  # HNSW parameter: size of dynamic candidate list
                    },
                ),
                # Text fields for filtering and metadata
                TextField("tenant_id"),
                TextField("metadata"),
            ]

            # Create index
            self.redis_client.ft(self.index_name).create_index(
                schema,
                definition=IndexDefinition(
                    prefix=["embedding:"], index_type=IndexType.HASH
                ),
            )

            logger.info(
                f"Created vector search index {self.index_name} with "
                f"dim={self.vector_dim}, metric={self.distance_metric}, type={self.index_type}"
            )

        except Exception as e:
            logger.error(
                f"Failed to create vector search index: {str(e)}", exc_info=True
            )
            raise EmbeddingCacheException(
                message=f"Failed to create vector search index: {str(e)}",
                error_code="EMBEDDING_INDEX_CREATION_ERROR",
                context={"index_name": self.index_name, "vector_dim": self.vector_dim},
            ) from e

    def _generate_hash(
        self,
        text: Union[str, List[str]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate hash for text and options for caching.

        Creates a deterministic hash based on text content, tenant ID, and options
        to enable efficient cache lookup and avoid recalculation for identical inputs.

        Args:
            text: Text or list of texts to hash
            tenant_id: Tenant identifier
            opts: Optional parameters

        Returns:
            Hash string for caching
        """
        # Create a dictionary with all inputs that affect the result
        hash_input = {"text": text, "tenant_id": tenant_id}

        # Add options if provided
        if opts:
            hash_input["opts"] = opts

        # Convert to JSON and hash
        hash_json = json.dumps(hash_input, sort_keys=True)
        return hashlib.md5(hash_json.encode()).hexdigest()
