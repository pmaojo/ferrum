from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from application.ports import (
    GraphRetrieverPort,
    OntologyValidatorPort,
    TracingPort,
)
from domain.entities import (
    Document,
    ScientificDomain,
    Triple,
    ValidationError,
    ValidationReport,
)

from .exceptions import GraphRAGException
from domain.utils.tracing import tracing_span



class IngestionService:
    """Domain service for document ingestion and knowledge graph construction.

    Orchestrates the process of extracting knowledge from documents using GraphRAG,
    validating against ontological constraints, and handling validation failures
    with repair suggestions.
    """

    def __init__(
        self,
        retriever: GraphRetrieverPort,
        validator: OntologyValidatorPort,
        tracer: Optional[TracingPort] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Initialize IngestionService with port dependencies.

        Args:
            retriever: GraphRAG port for document processing and entity extraction
            validator: Ontology validation port for consistency checking
            tracer: Optional tracing port for observability
        """
        self.retriever = retriever
        self.validator = validator
        self.tracer = tracer
        self.logger = logger or logging.getLogger(__name__)

    def process_documents(
        self,
        *,
        documents: List[Document],
        kg_id: str,
        tenant_id: str,
        ontology_version_id: str,
        domain: ScientificDomain = ScientificDomain.GENERAL,
        validate_incrementally: bool = True,
    ) -> ValidationReport:
        """Process documents through GraphRAG extraction and ontology validation.

        Extracts entities and relationships from documents, validates them against
        ontological constraints, and provides repair suggestions for validation failures.
        Supports scientific domain-specific processing for enhanced entity recognition.

        Args:
            documents: List of Document objects to process
            kg_id: Knowledge graph identifier for storage context
            tenant_id: Tenant identifier for multi-tenant isolation
            ontology_version_id: Ontology version for validation context
            domain: Scientific domain for specialized entity recognition (default: GENERAL)
            validate_incrementally: Whether to use delta validation for performance

        Returns:
            ValidationReport containing validation results and repair suggestions

        Raises:
            GraphRAGException: When document processing or validation fails
            ValidationError: When critical validation errors prevent processing

        Requirements addressed:
            - 1.1: Document processing through GraphRAG extraction
            - 1.2: Ontological validation of extracted knowledge
            - 1.3: Error handling with repair suggestions
            - 11.1: Scientific domain support for specialized processing
        """
        with tracing_span(
            self.tracer,
            name="ingestion.process_documents",
            tenant_id=tenant_id,
            kg_id=kg_id,
            document_count=len(documents),
        ):
            try:
                self.logger.info(
                    f"Starting document processing for kg_id={kg_id}, "
                    f"tenant_id={tenant_id}, document_count={len(documents)}"
                )

                # Extract document content for GraphRAG processing
                doc_contents = [doc.content for doc in documents]

                # Extract triples using GraphRAG
                self.logger.debug("Extracting triples using GraphRAG")
                extracted_triples = self._extract_triples_with_retry(
                    doc_contents=doc_contents, kg_id=kg_id, tenant_id=tenant_id
                )

                if not extracted_triples:
                    self.logger.warning("No triples extracted from documents")
                    return ValidationReport(
                        is_consistent=True,
                        unsat_classes=[],
                        repair_suggestions=[
                            "No knowledge extracted from documents. "
                            "Consider reviewing document content quality."
                        ],
                        tenant_id=tenant_id,
                        ontology_version_id=ontology_version_id,
                    )

                self.logger.info(f"Extracted {len(extracted_triples)} triples")

                # Validate extracted triples against ontology
                self.logger.debug("Validating triples against ontology")
                validation_report = self._validate_triples_with_error_handling(
                    triples=extracted_triples,
                    ontology_version_id=ontology_version_id,
                    tenant_id=tenant_id,
                    validate_incrementally=validate_incrementally,
                )

                # Record metrics if tracer available
                if self.tracer:
                    self.tracer.record_metric(
                        name="ingestion.triples_extracted",
                        value=len(extracted_triples),
                        tenant_id=tenant_id,
                        kg_id=kg_id,
                    )
                    self.tracer.record_metric(
                        name="ingestion.validation_success",
                        value=1.0 if validation_report.is_consistent else 0.0,
                        tenant_id=tenant_id,
                        kg_id=kg_id,
                    )

                self.logger.info(
                    f"Document processing completed. Consistent: {validation_report.is_consistent}, "
                    f"Unsatisfiable classes: {len(validation_report.unsat_classes)}"
                )

                return validation_report

            except Exception as e:
                self.logger.error(f"Document processing failed: {str(e)}", exc_info=True)

                if self.tracer:
                    self.tracer.record_metric(
                        name="ingestion.processing_errors",
                        value=1.0,
                        tenant_id=tenant_id,
                        error_type=type(e).__name__,
                    )

                # Convert to domain exception with context
                raise GraphRAGException(
                    message=f"Document processing failed: {str(e)}",
                    error_code="INGESTION_FAILED",
                    context={
                        "kg_id": kg_id,
                        "tenant_id": tenant_id,
                        "document_count": len(documents),
                        "original_error": str(e),
                    },
                ) from e

    def _extract_triples_with_retry(
        self,
        *,
        doc_contents: List[str],
        kg_id: str,
        tenant_id: str,
        max_retries: int = 3,
    ) -> List[Triple]:
        """Extract triples with retry logic for robustness.

        The method performs retry attempts with exponential backoff. After each
        failed extraction attempt the delay doubles (1s, 2s, 4s, ...)
        before the next retry.

        Args:
            doc_contents: List of document content strings
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier
            max_retries: Maximum number of retry attempts

        Returns:
            List of extracted Triple objects

        Raises:
            GraphRAGException: When extraction fails after all retries
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                self.logger.debug(f"GraphRAG extraction attempt {attempt + 1}")
                return self.retriever.index(
                    docs=doc_contents, kg_id=kg_id, tenant_id=tenant_id
                )
            except Exception as e:
                last_exception = e
                self.logger.warning(
                    f"GraphRAG extraction attempt {attempt + 1} failed: {str(e)}"
                )

                if attempt < max_retries:
                    delay = 2 ** attempt
                    self.logger.debug(
                        f"Waiting {delay} seconds before retrying extraction"
                    )
                    time.sleep(delay)
                    continue

        # All retries exhausted
        raise GraphRAGException(
            message=f"GraphRAG extraction failed after {max_retries + 1} attempts",
            error_code="EXTRACTION_FAILED",
            context={
                "kg_id": kg_id,
                "tenant_id": tenant_id,
                "attempts": max_retries + 1,
                "last_error": str(last_exception),
            },
        ) from last_exception

    def validate_triples(
        self,
        *,
        triples: List[Triple],
        ontology_version_id: str,
        tenant_id: str,
        validate_incrementally: bool = True,
    ) -> ValidationReport:
        """Validate triples using the configured ontology validator.

        This public method wraps the internal error-handling implementation to
        expose a stable API for other services while keeping the validation
        logic encapsulated.
        """

        return self._validate_triples_with_error_handling(
            triples=triples,
            ontology_version_id=ontology_version_id,
            tenant_id=tenant_id,
            validate_incrementally=validate_incrementally,
        )

    def _validate_triples_with_error_handling(
        self,
        *,
        triples: List[Triple],
        ontology_version_id: str,
        tenant_id: str,
        validate_incrementally: bool,
    ) -> ValidationReport:
        """Validate triples with comprehensive error handling and repair suggestions.

        Args:
            triples: List of Triple objects to validate
            ontology_version_id: Ontology version for validation
            tenant_id: Tenant identifier
            validate_incrementally: Whether to use delta validation

        Returns:
            ValidationReport with validation results and repair suggestions

        Raises:
            GraphRAGException: When validation process fails critically
        """
        try:
            if validate_incrementally:
                # Use delta validation for better performance
                self.logger.debug("Using incremental validation")
                validation_report = self.validator.validate_delta(
                    new_triples=triples,
                    existing_version_id=ontology_version_id,
                    tenant_id=tenant_id,
                )
            else:
                # Full validation
                self.logger.debug("Using full validation")
                validation_report = self.validator.validate(
                    triples=triples, ontology_version_id=ontology_version_id
                )

            # Enhance repair suggestions if validation failed
            if not validation_report.is_consistent:
                enhanced_suggestions = self._enhance_repair_suggestions(
                    validation_report=validation_report, triples=triples
                )

                # Create enhanced validation report
                validation_report = ValidationReport(
                    is_consistent=validation_report.is_consistent,
                    unsat_classes=validation_report.unsat_classes,
                    repair_suggestions=enhanced_suggestions,
                    tenant_id=validation_report.tenant_id,
                    ontology_version_id=validation_report.ontology_version_id,
                    explanation=validation_report.explanation,
                )

            return validation_report

        except Exception as e:
            self.logger.error(f"Ontology validation failed: {str(e)}", exc_info=True)

            # Return a validation report indicating failure with suggestions
            return ValidationReport(
                is_consistent=False,
                unsat_classes=["ValidationProcessFailed"],
                repair_suggestions=[
                    f"Validation process failed: {str(e)}",
                    "Check ontology version availability and format",
                    "Verify triple format and content",
                    "Consider using full validation instead of incremental",
                ],
                tenant_id=tenant_id,
                ontology_version_id=ontology_version_id,
                explanation=str(e),
            )

    def _enhance_repair_suggestions(
        self, *, validation_report: ValidationReport, triples: List[Triple]
    ) -> List[str]:
        """Enhance repair suggestions with context-specific guidance.

        Args:
            validation_report: Original validation report
            triples: Triples that were validated

        Returns:
            Enhanced list of repair suggestions
        """
        enhanced_suggestions = list(validation_report.repair_suggestions)

        # Add context-specific suggestions based on unsatisfiable classes
        if validation_report.unsat_classes:
            enhanced_suggestions.extend(
                [
                    f"Review class definitions for: {', '.join(validation_report.unsat_classes)}",
                    "Check for conflicting domain/range constraints",
                    "Verify cardinality restrictions are not violated",
                ]
            )

        # Add suggestions based on triple patterns
        predicates = {triple.predicate for triple in triples}
        if len(predicates) > 50:
            enhanced_suggestions.append(
                "Large number of unique predicates detected. "
                "Consider consolidating similar relationships."
            )

        # Add general guidance
        enhanced_suggestions.extend(
            [
                "Use ontology visualization tools to identify constraint conflicts",
                "Consider incremental validation for large knowledge bases",
                "Review source documents for data quality issues",
            ]
        )

        return enhanced_suggestions
