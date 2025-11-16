"""Use case for generating project scope documents."""

from dataclasses import dataclass

from application.exceptions import ValidationError
from application.ports import ScopeGeneratorPort
from application.use_cases.base_use_case import BaseUseCase


@dataclass
class GenerateScopeDocumentRequest:
    """Input for scope document generation."""

    description: str
    tenant_id: str


@dataclass
class GenerateScopeDocumentResponse:
    """Scope document generation result."""

    scope_document: str


class GenerateScopeDocumentUseCase(
    BaseUseCase[GenerateScopeDocumentRequest, GenerateScopeDocumentResponse]
):
    """Generate scope documents using the configured generator port."""

    def __init__(self, generator: ScopeGeneratorPort):
        super().__init__()
        self.generator = generator

    async def _execute_internal(
        self, request: GenerateScopeDocumentRequest
    ) -> GenerateScopeDocumentResponse:
        scope = self.generator.generate_scope_document(
            description=request.description, tenant_id=request.tenant_id
        )
        return GenerateScopeDocumentResponse(scope_document=scope)

    def _validate_request_internal(
        self, request: GenerateScopeDocumentRequest
    ) -> None:
        if not request.description.strip():
            raise ValidationError("description cannot be empty", field="description")
