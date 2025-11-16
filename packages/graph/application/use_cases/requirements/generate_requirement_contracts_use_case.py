"""Use case for generating contracts from requirement text."""
from __future__ import annotations

from dataclasses import dataclass

from application.contracts import Contract, Precondition, Postcondition, Invariant
from application.exceptions import ValidationError
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseRequestDTO, BaseResponseDTO
from application.use_cases.knowledge_graph.validate_knowledge_graph_use_case import (
    ValidationRule as BaseValidationRule,
)
from application.ports.requirement_parser_port import RequirementParserPort


@dataclass
class ValidationRule(BaseValidationRule):
    """Validation rule with associated contract kind."""

    kind: str  # 'precondition', 'postcondition' or 'invariant'


@dataclass
class GenerateRequirementContractsRequest(BaseRequestDTO):
    """Request containing raw requirement text."""

    requirements: str


@dataclass
class GenerateRequirementContractsResponse(BaseResponseDTO):
    """Response containing the assembled contract."""

    contract: Contract | None = None


class GenerateRequirementContractsUseCase(
    BaseUseCase[GenerateRequirementContractsRequest, GenerateRequirementContractsResponse]
):
    """Parse requirements and assemble contract objects."""

    def __init__(self, parser: RequirementParserPort) -> None:
        super().__init__()
        self.parser = parser

    def _validate_request_internal(
        self, request: GenerateRequirementContractsRequest
    ) -> None:
        if not request.requirements or not request.requirements.strip():
            raise ValidationError("requirements are required", field="requirements")

    async def _execute_internal(
        self, request: GenerateRequirementContractsRequest
    ) -> GenerateRequirementContractsResponse:
        rules = self.parser.parse(request.requirements)
        contract = Contract()
        for rule in rules:
            kind = getattr(rule, "kind", "invariant").lower()
            if kind == "precondition":
                contract.preconditions.append(Precondition(rule=rule))
            elif kind == "postcondition":
                contract.postconditions.append(Postcondition(rule=rule))
            else:
                contract.invariants.append(Invariant(rule=rule))
        return GenerateRequirementContractsResponse(
            success=True, processing_time_ms=0.0, contract=contract
        )
