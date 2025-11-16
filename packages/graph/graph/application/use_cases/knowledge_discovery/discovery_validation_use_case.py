"""Use case for validating hypotheses."""

from dataclasses import dataclass
from typing import List

from application.ports.knowledge_discovery import DiscoveryValidationPort
from application.use_cases.base_use_case import BaseUseCase
from domain.knowledge_discovery import Hypothesis, ValidationResult


@dataclass
class DiscoveryValidationRequest:
    hypotheses: List[Hypothesis]
    ontology_version_id: str
    tenant_id: str


@dataclass
class DiscoveryValidationResponse:
    results: List[ValidationResult]


class DiscoveryValidationUseCase(
    BaseUseCase[DiscoveryValidationRequest, DiscoveryValidationResponse]
):
    """Validate hypotheses using ontology constraints."""

    def __init__(self, validator: DiscoveryValidationPort) -> None:
        super().__init__()
        self._validator = validator

    async def _execute_internal(
        self, request: DiscoveryValidationRequest
    ) -> DiscoveryValidationResponse:
        results = self._validator.validate(
            hypotheses=request.hypotheses,
            ontology_version_id=request.ontology_version_id,
            tenant_id=request.tenant_id,
        )
        return DiscoveryValidationResponse(results=results)
