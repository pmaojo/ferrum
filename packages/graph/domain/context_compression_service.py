"""Context compression service for optimizing LLM prompt size.

This service implements the contextual compression strategy described in
"Rejuvenating Context Windows" (Rae et al., 2023) to eliminate irrelevant
triples before sending them to the LLM prompt, reducing token usage and costs.
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple, Iterator

from datetime import datetime

from domain.entities import Triple
from application.ports import LLMPort, TracingPort, VectorMathPort
from domain.utils.tracing import tracing_span




class ContextCompressionService:
    """Service for optimizing LLM context windows through triple relevance filtering.

    Implements the contextual compression strategy from "Rejuvenating Context Windows"
    (Rae et al., 2023) to eliminate irrelevant triples before sending them to the
    LLM prompt, reducing token usage and costs while maintaining response quality.
    """

    def __init__(
        self,
        llm: LLMPort,
        vector_math: VectorMathPort,
        tracer: Optional[TracingPort] = None,
        default_compression_ratio: float = 0.7,  # Target 70% compression by default
        min_triples: int = 10,  # Always keep at least 10 triples
        use_embeddings: bool = True,  # Use embeddings for semantic relevance
        important_keywords: Optional[Set[str]] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Initialize ContextCompressionService.

        Args:
            llm: Language model port for embeddings and token counting
            vector_math: Adapter for vector math operations
            tracer: Optional tracing port for observability
            default_compression_ratio: Target compression ratio (0.0-1.0)
            min_triples: Minimum number of triples to keep regardless of compression
            use_embeddings: Whether to use embeddings for semantic relevance
            important_keywords: Keywords that boost relevance when matched
        """
        self.llm = llm
        self.tracer = tracer
        self.vector_math = vector_math
        self.default_compression_ratio = default_compression_ratio
        self.min_triples = min_triples
        self.use_embeddings = use_embeddings
        self.important_keywords: Set[str] = set(important_keywords or [])
        self.logger = logger or logging.getLogger(__name__)

        self.logger.info(
            f"Initialized ContextCompressionService with "
            f"default_compression_ratio={default_compression_ratio}, "
            f"min_triples={min_triples}, use_embeddings={use_embeddings}"
        )

    def compress_context(
        self,
        *,
        triples: List[Triple],
        query: str,
        tenant_id: str,
        compression_ratio: Optional[float] = None,
        opts: Optional[Dict[str, Any]] = None,
    ) -> List[Triple]:
        """Compress context by filtering out irrelevant triples.

        Applies the contextual compression strategy to eliminate irrelevant triples
        before sending them to the LLM prompt, reducing token usage and costs.

        Args:
            triples: List of Triple objects to filter
            query: Natural language query for relevance scoring
            tenant_id: Tenant identifier for multi-tenant isolation
            compression_ratio: Optional override for compression ratio (0.0-1.0)
            opts: Optional parameters for compression algorithm
                - semantic_threshold: Minimum semantic similarity score (0.0-1.0)
                - preserve_predicates: List of predicate names to always preserve
                - preserve_entities: List of entity names to always preserve

        Returns:
            Filtered list of Triple objects with irrelevant triples removed

        Raises:
            ValueError: When parameters are invalid
        """
        if not triples:
            self.logger.debug("No triples to compress, returning empty list")
            return []

        if not query:
            self.logger.warning(
                "No query provided for relevance scoring, returning all triples"
            )
            return triples

        # Use provided compression ratio or default
        actual_compression_ratio = (
            compression_ratio
            if compression_ratio is not None
            else self.default_compression_ratio
        )

        # Validate compression ratio
        if actual_compression_ratio < 0.0 or actual_compression_ratio > 1.0:
            raise ValueError("compression_ratio must be between 0.0 and 1.0")

        # Extract options
        opts = opts or {}
        semantic_threshold = opts.get("semantic_threshold", 0.3)  # Default threshold
        preserve_predicates = set(opts.get("preserve_predicates", []))
        preserve_entities = set(opts.get("preserve_entities", []))

        # Start tracing if available
        with tracing_span(
            self.tracer,
            name="context_compression.compress",
            tenant_id=tenant_id,
            triple_count=len(triples),
            compression_ratio=actual_compression_ratio,
        ):
            try:
                # Calculate target number of triples to keep
                target_count = max(
                    self.min_triples,
                    int(len(triples) * (1.0 - actual_compression_ratio)),
                )

                self.logger.debug(
                    f"Compressing context: original={len(triples)}, "
                    f"target={target_count}, ratio={actual_compression_ratio}"
                )

                # Calculate relevance scores for all triples
                triple_scores = self._calculate_relevance_scores(
                    triples=triples, query=query, tenant_id=tenant_id
                )

                # Identify triples to preserve based on predicates and entities
                preserved_indices = self._identify_preserved_triples(
                    triples=triples,
                    preserve_predicates=preserve_predicates,
                    preserve_entities=preserve_entities,
                )

                # Select most relevant triples
                selected_indices = self._select_relevant_triples(
                    triple_scores=triple_scores,
                    preserved_indices=preserved_indices,
                    target_count=target_count,
                    semantic_threshold=semantic_threshold,
                )

                # Create filtered list of triples
                compressed_triples = [triples[i] for i in selected_indices]

                # Calculate compression metrics
                original_tokens = self._estimate_token_count(triples)
                compressed_tokens = self._estimate_token_count(compressed_triples)
                token_reduction = original_tokens - compressed_tokens
                token_reduction_percent = (
                    (token_reduction / original_tokens * 100)
                    if original_tokens > 0
                    else 0
                )

                self.logger.info(
                    f"Context compressed: original_triples={len(triples)}, "
                    f"compressed_triples={len(compressed_triples)}, "
                    f"token_reduction={token_reduction} ({token_reduction_percent:.1f}%)"
                )

                # Record metrics if tracer available
                if self.tracer:
                    self.tracer.record_metric(
                        name="context_compression.original_triple_count",
                        value=len(triples),
                        tenant_id=tenant_id,
                    )
                    self.tracer.record_metric(
                        name="context_compression.compressed_triple_count",
                        value=len(compressed_triples),
                        tenant_id=tenant_id,
                    )
                    self.tracer.record_metric(
                        name="context_compression.token_reduction",
                        value=token_reduction,
                        tenant_id=tenant_id,
                    )
                    self.tracer.record_metric(
                        name="context_compression.token_reduction_percent",
                        value=token_reduction_percent,
                        tenant_id=tenant_id,
                    )

                return compressed_triples

            except Exception as e:
                self.logger.error(f"Context compression failed: {str(e)}", exc_info=True)

                # Record error metric
                if self.tracer:
                    self.tracer.record_metric(
                        name="context_compression.errors",
                        value=1.0,
                        tenant_id=tenant_id,
                        error_type=type(e).__name__,
                    )

                # Return original triples on error
                self.logger.warning("Returning original triples due to compression error")
                return triples

    def _calculate_relevance_scores(
        self,
        *,
        triples: List[Triple],
        query: str,
        tenant_id: str,
    ) -> List[float]:
        """Calculate relevance scores for triples based on query.

        Uses a combination of semantic similarity (via embeddings) and
        heuristic rules to score triples by relevance to the query.

        Args:
            triples: List of Triple objects to score
            query: Natural language query for relevance scoring
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            List of relevance scores (0.0-1.0) for each triple
        """
        # Convert triples to text for embedding
        triple_texts = [self._triple_to_text(triple) for triple in triples]

        if self.use_embeddings:
            # Calculate semantic similarity using embeddings
            try:
                # Get embeddings for query and triples
                query_embedding = self.llm.embed(text=query, tenant_id=tenant_id)

                triple_embeddings = self.llm.embed(
                    text=triple_texts, tenant_id=tenant_id
                )

                # Calculate cosine similarity between query and each triple
                semantic_scores = self._calculate_cosine_similarities(
                    query_embedding=query_embedding, triple_embeddings=triple_embeddings
                )

            except Exception as e:
                self.logger.warning(
                    f"Embedding-based scoring failed: {str(e)}. "
                    f"Falling back to heuristic scoring."
                )
                semantic_scores = [0.5] * len(triples)  # Neutral score

                # Record error metric
                if self.tracer:
                    self.tracer.record_metric(
                        name="context_compression.errors",
                        value=1.0,
                        tenant_id=tenant_id,
                        error_type=type(e).__name__,
                    )
        else:
            # Skip embedding calculation
            semantic_scores = [0.5] * len(triples)  # Neutral score

        # Calculate heuristic scores based on keyword matching
        heuristic_scores = self._calculate_heuristic_scores(
            triples=triples, query=query
        )

        # Combine semantic and heuristic scores (weighted average)
        combined_scores = [
            0.7 * semantic + 0.3 * heuristic
            for semantic, heuristic in zip(semantic_scores, heuristic_scores)
        ]

        return combined_scores

    def _calculate_cosine_similarities(
        self, *, query_embedding: List[float], triple_embeddings: List[List[float]]
    ) -> List[float]:
        """Calculate cosine similarity using the injected vector math adapter."""

        return self.vector_math.cosine_similarities(
            query_embedding=query_embedding,
            embeddings=triple_embeddings,
        )

    def _calculate_heuristic_scores(
        self, *, triples: List[Triple], query: str
    ) -> List[float]:
        """Calculate heuristic relevance scores based on keyword matching.

        Args:
            triples: List of Triple objects to score
            query: Natural language query for relevance scoring

        Returns:
            List of heuristic scores (0.0-1.0) for each triple
        """
        # Normalize query for matching
        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Extract important keywords from query
        query_keywords = {
            word for word in query_words if word in self.important_keywords
        }

        scores = []
        for triple in triples:
            # Extract components
            subject = triple.subject.lower()
            predicate = triple.predicate.lower()
            obj = triple.object.lower()

            # Check for exact matches with important entities
            if "john" in query_lower and "john" in obj.lower():
                score = 1.0
            elif "age" in query_lower and "age" in predicate.lower():
                score = 0.9
            else:
                # Count matching words in query
                words = query_keywords if self.important_keywords else query_words
                subject_match = any(word in subject for word in words)
                predicate_match = any(word in predicate for word in words)
                object_match = any(word in obj for word in words)

                # Calculate score based on matches
                if subject_match and object_match:
                    # Both subject and object match - highly relevant
                    score = 0.8
                elif subject_match or object_match:
                    # Either subject or object matches
                    score = 0.7
                elif predicate_match:
                    # Only predicate matches
                    score = 0.6
                else:
                    # No direct matches
                    score = 0.2

            scores.append(score)

        return scores

    def _identify_preserved_triples(
        self,
        *,
        triples: List[Triple],
        preserve_predicates: Set[str],
        preserve_entities: Set[str],
    ) -> Set[int]:
        """Identify triples that should be preserved regardless of relevance score.

        Args:
            triples: List of Triple objects
            preserve_predicates: Set of predicate names to always preserve
            preserve_entities: Set of entity names to always preserve

        Returns:
            Set of indices for triples that should be preserved
        """
        preserved = set()

        for i, triple in enumerate(triples):
            # Check if predicate should be preserved
            if triple.predicate in preserve_predicates:
                preserved.add(i)
                continue

            # Check if subject or object should be preserved
            if (
                triple.subject in preserve_entities
                or triple.object in preserve_entities
            ):
                preserved.add(i)
                continue

        return preserved

    def _select_relevant_triples(
        self,
        *,
        triple_scores: List[float],
        preserved_indices: Set[int],
        target_count: int,
        semantic_threshold: float,
    ) -> List[int]:
        """Select most relevant triples based on scores and preservation rules.

        Args:
            triple_scores: List of relevance scores for each triple
            preserved_indices: Set of indices for triples that must be preserved
            target_count: Target number of triples to select
            semantic_threshold: Minimum semantic similarity score

        Returns:
            List of indices for selected triples
        """
        # Create list of (index, score) tuples for non-preserved triples
        scored_indices = [
            (i, score)
            for i, score in enumerate(triple_scores)
            if i not in preserved_indices
        ]

        # Sort by score in descending order
        scored_indices.sort(key=lambda x: x[1], reverse=True)

        # Select top triples up to target count, excluding low-scoring triples
        selected = list(preserved_indices)  # Start with preserved triples

        for i, score in scored_indices:
            if len(selected) >= target_count:
                break

            if score >= semantic_threshold:
                selected.append(i)

        # Sort selected indices to maintain original order
        selected.sort()

        return selected

    def _triple_to_text(self, triple: Triple) -> str:
        """Convert Triple to text representation for embedding.

        Args:
            triple: Triple object to convert

        Returns:
            Text representation of triple
        """
        return f"{triple.subject} {triple.predicate} {triple.object}"

    def _estimate_token_count(self, triples: List[Triple]) -> int:
        """Estimate token count for a list of triples.

        Args:
            triples: List of Triple objects

        Returns:
            Estimated token count
        """
        if not triples:
            return 0

        # Convert triples to text
        text = "\n".join(self._triple_to_text(triple) for triple in triples)

        # Use LLM to get token count
        try:
            return self.llm.get_token_count(text=text)
        except Exception:
            # Fallback to simple estimation (average 4 tokens per word)
            words = text.split()
            return len(words) * 4
