from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from application.ports import (
    GraphRetrieverPort,
    QueryTranslatorPort,
    TracingPort,
)
from domain.utils.tracing import tracing_span
from domain.entities import Triple, ValidationReport

from .exceptions import GraphRAGException, ValidationError, QueryProcessingError
from .query_translation import QueryTranslationService
from .query_execution import QueryExecutionService
from .result_formatter import ResultFormatter
from .ambiguity_detector import AmbiguityDetector

logger = logging.getLogger(__name__)


class QueryService:
    """Domain service for natural language query processing and execution.

    Orchestrates the translation of natural language queries into graph queries,
    executes them against the knowledge graph, and formats results with explanations.
    """

    def __init__(
        self,
        translator: QueryTranslatorPort,
        retriever: GraphRetrieverPort,
        tracer: Optional[TracingPort] = None,
        *,
        sparql_translation_service: Optional[QueryTranslationService] = None,
        shacl_translation_service: Optional[QueryTranslationService] = None,
        translation_service: Optional[QueryTranslationService] = None,
        execution_service: Optional[QueryExecutionService] = None,
        formatter: Optional[ResultFormatter] = None,
        ambiguity_detector: Optional[AmbiguityDetector] = None,
    ) -> None:
        """Initialize QueryService with port dependencies.

        Args:
            translator: Query translation port for Cypher/GQL
            retriever: GraphRAG port for query execution
            tracer: Optional tracing port for observability
            sparql_translation_service: Optional translation service for SPARQL
            shacl_translation_service: Optional translation service for SHACL
            translation_service: Component for translation logic
            execution_service: Component for query execution
            formatter: Component for result formatting
            ambiguity_detector: Component for ambiguity detection
        """
        self.translator = translator
        self.retriever = retriever
        self.tracer = tracer
        self.ambiguity_detector = ambiguity_detector or AmbiguityDetector()
        self.translation_service = translation_service or QueryTranslationService(
            translator
        )
        self.sparql_translation_service = sparql_translation_service
        self.shacl_translation_service = shacl_translation_service
        self.execution_service = execution_service or QueryExecutionService(retriever)
        self.formatter = formatter or ResultFormatter(self.ambiguity_detector)

    def ask_graphrag(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, List[Triple]]:
        """Execute a raw GraphRAG query using the retriever service.

        This bypasses natural language translation and directly delegates
        execution to the configured ``QueryExecutionService``.  The method is
        small so it can be easily swapped or mocked when testing.

        Args:
            question: Natural language query.
            kg_id: Knowledge graph identifier.
            tenant_id: Tenant identifier.
            opts: Optional execution parameters forwarded to the retriever.

        Returns:
            Raw results returned by the underlying GraphRAG engine.
        """

        with tracing_span(
            self.tracer,
            name="query.ask_graphrag",
            tenant_id=tenant_id,
            kg_id=kg_id,
            question_length=len(question),
        ):
            return self.execution_service.run_query(
                question=question,
                kg_id=kg_id,
                tenant_id=tenant_id,
                query_opts=opts or {},
            )

    def _select_translation_service(self, language: str) -> QueryTranslationService:
        """Return translation service based on desired query language."""
        if language.lower() == "sparql" and self.sparql_translation_service:
            return self.sparql_translation_service
        if language.lower() == "shacl" and self.shacl_translation_service:
            return self.shacl_translation_service
        if language.lower() in {"sparql", "shacl"}:
            logger.warning(
                "%s translator not available, falling back to default", language
            )
        return self.translation_service

    def translate_to_sparql(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
    ) -> Tuple[str, str]:
        """Translate natural language question into SPARQL."""
        service = self._select_translation_service("sparql")
        return service.translate_with_fallback(
            question=question, kg_id=kg_id, tenant_id=tenant_id
        )

    def translate_to_shacl(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
    ) -> Tuple[str, str]:
        """Translate natural language question into SHACL."""
        service = self._select_translation_service("shacl")
        return service.translate_with_fallback(
            question=question, kg_id=kg_id, tenant_id=tenant_id
        )

    def execute_natural_language_query(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        user_id: str,
        query_language: str = "cypher",
        include_explanation: bool = True,
        include_subgraph: bool = True,
        max_results: int = 50,
        query_opts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute natural language query with translation and result formatting.

        Translates natural language questions into graph queries, executes them,
        and returns formatted results with explanations and metadata. Includes
        subgraph highlighting and ambiguous query detection.

        Args:
            question: Natural language query from user
            kg_id: Knowledge graph identifier to query
            tenant_id: Tenant identifier for multi-tenant isolation
            user_id: User identifier for query tracking
            query_language: "cypher", "sparql" or "shacl"
            include_explanation: Whether to include query explanation
            include_subgraph: Whether to include relevant subgraph highlighting
            max_results: Maximum number of results to return
            query_opts: Optional parameters for GraphRAG query execution

        Returns:
            Dictionary containing:
            - results: Query results (text or structured data)
            - explanation: Query translation explanation (if requested)
            - metadata: Query execution metadata (timing, result count, etc.)
            - suggestions: Alternative query suggestions if no results
            - subgraph: Relevant subgraph highlighting (if requested)
            - clarification_needed: Whether query is ambiguous and needs clarification

        Raises:
            GraphRAGException: When query processing fails
            ValidationError: When query parameters are invalid

        Requirements addressed:
            - 2.1: Natural language to graph query translation
            - 2.2: Query execution with contextual explanations
            - 2.3: Result formatting and subgraph highlighting
            - 2.4: Ambiguous query detection and clarification requests
        """
        with tracing_span(
            self.tracer,
            name="query.execute_natural_language",
            tenant_id=tenant_id,
            kg_id=kg_id,
            user_id=user_id,
            question_length=len(question),
        ):
            start_time = datetime.now()

            try:
                logger.info(
                    f"Processing natural language query for kg_id={kg_id}, "
                    f"tenant_id={tenant_id}, user_id={user_id}"
                )

                # Validate input parameters
                self._validate_query_parameters(
                    question=question,
                    kg_id=kg_id,
                    tenant_id=tenant_id,
                    max_results=max_results,
                )

                # Translate natural language to chosen query language
                logger.debug("Translating natural language query")
                translation_service = self._select_translation_service(query_language)
                (
                    translated_query,
                    explanation,
                ) = translation_service.translate_with_fallback(
                    question=question, kg_id=kg_id, tenant_id=tenant_id
                )

                # Execute query against knowledge graph
                logger.debug("Executing translated query")
                query_results = self.execution_service.run_query(
                    question=question,
                    kg_id=kg_id,
                    tenant_id=tenant_id,
                    query_opts=query_opts or {},
                )

                # Calculate execution time
                execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

                # Check for ambiguous queries and need for clarification (Requirement 2.4)
                logger.debug("Checking for query ambiguity")
                (
                    clarification_needed,
                    clarification_questions,
                ) = self.ambiguity_detector.detect(
                    question=question,
                    results=query_results,
                    translated_query=translated_query,
                )

                # Extract relevant subgraph if requested (Requirement 2.3)
                relevant_subgraph = None
                if include_subgraph and self.formatter.has_meaningful_results(
                    query_results
                ):
                    logger.debug("Extracting relevant subgraph")
                    relevant_subgraph = self.formatter.extract_relevant_subgraph(
                        results=query_results, kg_id=kg_id, tenant_id=tenant_id
                    )

                # Format results and generate response
                formatted_response = self.formatter.format_response(
                    results=query_results,
                    explanation=explanation if include_explanation else None,
                    translated_query=translated_query,
                    execution_time_ms=execution_time_ms,
                    max_results=max_results,
                    subgraph=relevant_subgraph,
                    clarification_needed=clarification_needed,
                    clarification_questions=clarification_questions,
                )

                # Generate alternative suggestions if no results
                if not self.formatter.has_meaningful_results(query_results):
                    formatted_response[
                        "suggestions"
                    ] = self._generate_query_suggestions(
                        original_question=question, kg_id=kg_id, tenant_id=tenant_id
                    )

                # Record metrics
                if self.tracer:
                    self.tracer.record_metric(
                        name="query.execution_time_ms",
                        value=execution_time_ms,
                        tenant_id=tenant_id,
                        kg_id=kg_id,
                    )
                    self.tracer.record_metric(
                        name="query.result_count",
                        value=len(formatted_response.get("results", [])),
                        tenant_id=tenant_id,
                        kg_id=kg_id,
                    )

                logger.info(
                    f"Query processing completed. Execution time: {execution_time_ms:.2f}ms, "
                    f"Results: {len(formatted_response.get('results', []))}"
                )

                return formatted_response

            except Exception as e:
                execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                logger.error("Query processing failed: %s", e, exc_info=True)

                if self.tracer:
                    self.tracer.record_metric(
                        name="query.processing_errors",
                        value=1.0,
                        tenant_id=tenant_id,
                        error_type=type(e).__name__,
                    )

                raise QueryProcessingError(
                    message=str(e),
                    kg_id=kg_id,
                    tenant_id=tenant_id,
                    query=question,
                    context={"execution_time_ms": execution_time_ms},
                ) from e

    def _validate_query_parameters(
        self, *, question: str, kg_id: str, tenant_id: str, max_results: int
    ) -> None:
        """Validate query parameters for correctness.

        Args:
            question: Natural language query
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier
            max_results: Maximum results limit

        Raises:
            ValidationError: When parameters are invalid
        """
        if not question or not question.strip():
            raise ValidationError("Question cannot be empty", param="question")

        # Check for invalid placeholder values
        if question.strip().lower() in ["string", "none", "null", "undefined"]:
            raise ValidationError(
                f"Invalid question placeholder: '{question.strip()}'. Please provide a real question.",
                param="question",
            )

        if len(question) > 10000:  # Reasonable limit
            raise ValidationError(
                "Question is too long (max 10,000 characters)", param="question"
            )

        if not kg_id or not kg_id.strip():
            raise ValidationError("Knowledge graph ID cannot be empty", param="kg_id")

        if not tenant_id or not tenant_id.strip():
            raise ValidationError("Tenant ID cannot be empty", param="tenant_id")

        if max_results <= 0 or max_results > 1000:
            raise ValidationError(
                "Max results must be between 1 and 1000", param="max_results"
            )

    def _generate_query_suggestions(
        self, *, original_question: str, kg_id: str, tenant_id: str
    ) -> List[str]:
        """Generate alternative query suggestions when no results found.

        Args:
            original_question: Original user question
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Returns:
            List of suggested alternative queries
        """
        suggestions = []

        # Extract key terms from original question
        key_terms = self._extract_key_terms(original_question)

        if key_terms:
            suggestions.extend(
                [
                    f"Try searching for individual terms: {', '.join(key_terms[:3])}",
                    f"Use broader terms related to: {key_terms[0] if key_terms else 'your topic'}",
                    (
                        f"Ask about relationships: 'What is connected to {key_terms[0]}?'"
                        if key_terms
                        else None
                    ),
                ]
            )

        # Add general suggestions
        suggestions.extend(
            [
                "Try using simpler, more specific language",
                "Ask about entities or relationships you know exist in the data",
                "Use 'what', 'who', 'where', 'when' question formats",
                "Break complex questions into smaller parts",
            ]
        )

        # Filter out None values and return
        return [s for s in suggestions if s is not None]

    def _extract_key_terms(self, question: str) -> List[str]:
        """Extract key terms from natural language question.

        Args:
            question: Natural language question

        Returns:
            List of key terms extracted from question
        """
        # Simple keyword extraction - could be enhanced with NLP
        import re

        # Remove common stop words and extract meaningful terms
        stop_words = {
            "what",
            "who",
            "where",
            "when",
            "why",
            "how",
            "is",
            "are",
            "was",
            "were",
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "about",
            "can",
            "could",
            "would",
            "should",
            "do",
            "does",
            "did",
            "have",
            "has",
            "had",
            "will",
            "would",
            "could",
            "should",
        }

        # Extract words (alphanumeric sequences)
        words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9]*\b", question.lower())

        # Filter out stop words and short words
        key_terms = [word for word in words if word not in stop_words and len(word) > 2]

        # Return unique terms, preserving order
        seen = set()
        unique_terms = []
        for term in key_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)

        return unique_terms[:10]  # Limit to top 10 terms
