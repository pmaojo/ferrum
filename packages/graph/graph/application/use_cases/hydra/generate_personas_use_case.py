"""Use case for generating user personas."""

from dataclasses import dataclass
from typing import List

from application.exceptions import ValidationError
from application.ports import PersonaGeneratorPort
from application.use_cases.base_use_case import BaseUseCase


@dataclass
class GeneratePersonasRequest:
    """Input for persona generation."""

    description: str
    tenant_id: str
    num_personas: int = 3


@dataclass
class GeneratePersonasResponse:
    """Persona generation result."""

    personas: List[str]


class GeneratePersonasUseCase(
    BaseUseCase[GeneratePersonasRequest, GeneratePersonasResponse]
):
    """Generate personas using the configured generator port."""

    def __init__(self, generator: PersonaGeneratorPort):
        super().__init__()
        self.generator = generator

    async def _execute_internal(
        self, request: GeneratePersonasRequest
    ) -> GeneratePersonasResponse:
        personas = self.generator.generate_personas(
            description=request.description,
            tenant_id=request.tenant_id,
            num_personas=request.num_personas,
        )
        return GeneratePersonasResponse(personas=personas)

    def _validate_request_internal(self, request: GeneratePersonasRequest) -> None:
        if not request.description.strip():
            raise ValidationError("description cannot be empty", field="description")
        if request.num_personas <= 0:
            raise ValidationError(
                "num_personas must be positive", field="num_personas"
            )
