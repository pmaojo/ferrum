"""Fixes the AttributeError by using the query translator to translate the query instead of the graph retriever."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from application.ports import (
    GraphRetrieverPort,
    LLMPort,
    QueryTranslatorPort,
    TracingPort,
)
from domain.entities import ScientificDomain, Triple
from domain.exceptions import GraphRAGException, ValidationError
from domain.services import QueryService


@dataclass
class QueryKnowledgeGraphRequest:
    """Request to query knowledge graph with natural language."""

    question: str
    kg_id: str
    tenant_id: str
    user_id: str
    domain: ScientificDomain
    options: Optional[Dict[str, Any]] = None


@dataclass
class QueryKnowledgeGraphResponse:
    """Response from knowledge graph query."""

    answer: str
    relevant_triples: List[Triple]
    translated_query: str
    query_explanation: str
    confidence_score: float
    processing_time_ms: float
    success: bool
    error_message: Optional[str] = None


class QueryKnowledgeGraphUseCase:
    """Use case for natural language querying of knowledge graphs."""

    def __init__(
        self,
        query_service: QueryService,
        retriever_port: GraphRetrieverPort,
        translator_port: QueryTranslatorPort,
        tracer_port: TracingPort,
        llm_port: LLMPort,
    ):
        self.query_service = query_service
        self.retriever_port = retriever_port
        self.translator_port = translator_port
        self.tracer_port = tracer_port
        self.llm_port = llm_port

    async def execute(
        self, request: QueryKnowledgeGraphRequest
    ) -> QueryKnowledgeGraphResponse:
        """Execute natural language query against knowledge graph."""

        with self.tracer_port.start_span(
            name="query_knowledge_graph",
            tenant_id=request.tenant_id,
            kg_id=request.kg_id,
            user_id=request.user_id,
            domain=request.domain.value,
        ) as span:
            try:
                # Validate input
                self._validate_request(request)

                # Translate natural language to graph query
                translated_query, explanation = await self._translate_query(request)

                # Execute query against knowledge graph
                query_result = await self._execute_query(request)

                # Format response with context
                formatted_answer = await self._format_answer(
                    query_result, request.question, request.tenant_id
                )

                # Extract relevant triples if available
                relevant_triples = self._extract_relevant_triples(query_result)

                # Calculate confidence score
                confidence_score = self._calculate_confidence(
                    query_result, request.question
                )

                # Record metrics
                self.tracer_port.record_metric(
                    name="query_latency_ms",
                    value=span.duration_ms,
                    tenant_id=request.tenant_id,
                    domain=request.domain.value,
                )

                return QueryKnowledgeGraphResponse(
                    answer=formatted_answer,
                    relevant_triples=relevant_triples,
                    translated_query=translated_query,
                    query_explanation=explanation,
                    confidence_score=confidence_score,
                    processing_time_ms=span.duration_ms,
                    success=True,
                )

            except (ValidationError, GraphRAGException) as e:
                self.tracer_port.record_metric(
                    name="query_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )

                return QueryKnowledgeGraphResponse(
                    answer="",
                    relevant_triples=[],
                    translated_query="",
                    query_explanation="",
                    confidence_score=0.0,
                    processing_time_ms=span.duration_ms,
                    success=False,
                    error_message=str(e),
                )

    def _validate_request(self, request: QueryKnowledgeGraphRequest) -> None:
        """Validate the query request."""
        if not request.question.strip():
            raise ValidationError("Query question cannot be empty")

        if not request.kg_id or not request.tenant_id:
            raise ValidationError("Knowledge graph ID and tenant ID are required")

        # Check query length limits
        if len(request.question) > 1000:
            raise ValidationError("Query question exceeds maximum length")

    async def _translate_query(
        self, request: QueryKnowledgeGraphRequest
    ) -> tuple[str, str]:
        """Translate natural language to graph query."""
        return self.translator_port.translate(
            natural_language=request.question,
            kg_id=request.kg_id,
            tenant_id=request.tenant_id,
        )

    async def _execute_query(
        self, request: QueryKnowledgeGraphRequest
    ) -> Union[str, List[Triple]]:
        """Execute query against knowledge graph."""
        return self.retriever_port.run(
            question=request.question,
            kg_id=request.kg_id,
            tenant_id=request.tenant_id,
            opts=request.options or {},
        )

    async def _format_answer(
        self, query_result: Union[str, List[Triple]], question: str, tenant_id: str
    ) -> str:
        """Format query result into natural language answer."""
        if isinstance(query_result, str):
            return query_result

        # Convert triples to natural language using LLM
        triples_text = "\n".join(
            [
                f"{triple.subject} {triple.predicate} {triple.object}"
                for triple in query_result
            ]
        )

        prompt = f"""
        Based on the following knowledge graph information, answer the question: "{question}"

        Knowledge Graph Data:
        {triples_text}

        Provide a clear, concise answer based on the available information.
        """

        return self.llm_port.generate(
            prompt=prompt,
            tenant_id=tenant_id,
            opts={"temperature": 0.3, "max_tokens": 500},
        )

    def _extract_relevant_triples(
        self, query_result: Union[str, List[Triple]]
    ) -> List[Triple]:
        """Extract relevant triples from query result."""
        if isinstance(query_result, list):
            return query_result
        return []

    def _calculate_confidence(
        self, query_result: Union[str, List[Triple]], question: str
    ) -> float:
        """Calculate confidence score for the query result."""
        if isinstance(query_result, list) and query_result:
            # Higher confidence for structured results
            return min(0.9, 0.5 + (len(query_result) * 0.1))
        elif isinstance(query_result, str) and query_result.strip():
            # Medium confidence for text results
            return 0.7
        else:
            # Low confidence for empty results
            return 0.1
