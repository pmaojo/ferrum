from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol

from application.exceptions import ApplicationError, ValidationError
from application.ports import TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, TenantScopedRequestDTO


@dataclass
class ValidationRule:
    """Rule used for validating a knowledge graph."""

    name: str
    expression: str


@dataclass
class ValidateKnowledgeGraphRequest(TenantScopedRequestDTO):
    """Request to validate a knowledge graph with custom rules."""

    kg_id: str
    rules: List[ValidationRule]


@dataclass
class ValidateKnowledgeGraphResponse(BaseResponseDTO):
    """Response containing validation results."""

    is_valid: bool | None = None
    details: List[Dict[str, Any]] | None = None


class KnowledgeGraphValidatorPort(Protocol):
    """Port for knowledge graph validation."""

    def validate(
        self, *, kg_id: str, tenant_id: str, rules: List[ValidationRule]
    ) -> tuple[bool, List[Dict[str, Any]]]: ...


class ValidateKnowledgeGraphUseCase(
    BaseUseCase[ValidateKnowledgeGraphRequest, ValidateKnowledgeGraphResponse]
):
    """Use case for rule-based knowledge graph validation."""

    def __init__(
        self, validator: KnowledgeGraphValidatorPort, tracer: TracingPort
    ) -> None:
        super().__init__()
        self.validator = validator
        self.tracer = tracer

    def _validate_request_internal(
        self, request: ValidateKnowledgeGraphRequest
    ) -> None:
        if not request.kg_id:
            raise ValidationError(message="kg_id is required", field="kg_id")

    async def _execute_internal(
        self, request: ValidateKnowledgeGraphRequest
    ) -> ValidateKnowledgeGraphResponse:
        with self.tracer.start_span(
            name="validate_knowledge_graph",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            kg_id=request.kg_id,
        ) as span:
            try:
                valid, details = self.validator.validate(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    rules=request.rules,
                )
                return ValidateKnowledgeGraphResponse(
                    success=True,
                    processing_time_ms=span.duration_ms,
                    is_valid=valid,
                    details=details,
                )
            except Exception as e:
                if isinstance(e, ValidationError):
                    raise
                raise ApplicationError(
                    message=f"Validation failed: {e}",
                    error_code="GRAPH_VALIDATION_FAILED",
                )
