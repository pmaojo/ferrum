"""Use case for indexing documents and extracting knowledge graphs."""

from dataclasses import dataclass
from typing import List, Optional

from application.ports import (
    GraphRetrieverPort,
    LLMPort,
    OntologyValidatorPort,
    TracingPort,
)
from domain.entities import ScientificDomain, Triple, ValidationReport
from domain.exceptions import GraphRAGException, ValidationError
from domain.services import IngestionService


@dataclass
class IndexDocumentsRequest:
    """Request to index documents and extract knowledge graph."""

    documents: List[str]
    kg_id: str
    tenant_id: str
    domain: ScientificDomain
    ontology_version_id: str
    user_id: str


@dataclass
class IndexDocumentsResponse:
    """Response from document indexing operation."""

    extracted_triples: List[Triple]
    validation_report: ValidationReport
    processing_time_ms: float
    success: bool
    error_message: Optional[str] = None


class IndexDocumentsUseCase:
    """Use case for processing documents and creating validated knowledge graphs."""

    def __init__(
        self,
        ingestion_service: IngestionService,
        retriever_port: GraphRetrieverPort,
        validator_port: OntologyValidatorPort,
        tracer_port: TracingPort,
        llm_port: LLMPort,
    ):
        self.ingestion_service = ingestion_service
        self.retriever_port = retriever_port
        self.validator_port = validator_port
        self.tracer_port = tracer_port
        self.llm_port = llm_port

    async def execute(self, request: IndexDocumentsRequest) -> IndexDocumentsResponse:
        """Execute document indexing with validation and error handling."""

        with self.tracer_port.start_span(
            name="index_documents",
            tenant_id=request.tenant_id,
            kg_id=request.kg_id,
            user_id=request.user_id,
            domain=request.domain.value,
        ) as span:
            try:
                # Validate input
                self._validate_request(request)

                # Extract triples using GraphRAG
                extracted_triples = await self._extract_triples(request)

                # Validate against ontology
                validation_report = await self._validate_triples(
                    extracted_triples, request.ontology_version_id
                )

                # Record metrics
                self.tracer_port.record_metric(
                    name="triples_extracted",
                    value=len(extracted_triples),
                    tenant_id=request.tenant_id,
                    domain=request.domain.value,
                )

                return IndexDocumentsResponse(
                    extracted_triples=extracted_triples,
                    validation_report=validation_report,
                    processing_time_ms=span.duration_ms,
                    success=True,
                )

            except (ValidationError, GraphRAGException) as e:
                self.tracer_port.record_metric(
                    name="indexing_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )

                return IndexDocumentsResponse(
                    extracted_triples=[],
                    validation_report=ValidationReport(
                        is_consistent=False,
                        unsat_classes=[],
                        repair_suggestions=[str(e)],
                        tenant_id=request.tenant_id,
                        ontology_version_id=request.ontology_version_id,
                        explanation=str(e),
                    ),
                    processing_time_ms=span.duration_ms,
                    success=False,
                    error_message=str(e),
                )

    def _validate_request(self, request: IndexDocumentsRequest) -> None:
        """Validate the indexing request."""
        if not request.documents:
            raise ValidationError("No documents provided for indexing")

        if not request.kg_id or not request.tenant_id:
            raise ValidationError("Knowledge graph ID and tenant ID are required")

        # Check document size limits based on subscription
        total_size = sum(len(doc) for doc in request.documents)
        if total_size > 10_000_000:  # 10MB limit
            raise ValidationError("Document size exceeds maximum limit")

    async def _extract_triples(self, request: IndexDocumentsRequest) -> List[Triple]:
        """Extract triples from documents using GraphRAG."""
        return self.retriever_port.index(
            docs=request.documents,
            kg_id=request.kg_id,
            tenant_id=request.tenant_id,
            domain=request.domain,
        )

    async def _validate_triples(
        self, triples: List[Triple], ontology_version_id: str
    ) -> ValidationReport:
        """Validate extracted triples against ontology."""
        return self.validator_port.validate(
            triples=triples, ontology_version_id=ontology_version_id
        )
