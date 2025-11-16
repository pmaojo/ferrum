"""API endpoints for processing feature requests through HyDRA."""

from fastapi import APIRouter, Depends

from adapters.hydra import (
    CompetencyQuestionGeneratorAdapter,
    PersonaGeneratorAdapter,
    ScopeGeneratorAdapter,
)
from application.feature_request_handler import FeatureRequestHandler
from application.use_cases.hydra.generate_competency_questions_use_case import (
    GenerateCompetencyQuestionsUseCase,
)
from application.use_cases.hydra.generate_personas_use_case import (
    GeneratePersonasUseCase,
)
from application.use_cases.hydra.generate_scope_document_use_case import (
    GenerateScopeDocumentUseCase,
)
from permagraph.repository import InMemoryGraphRepository
from ui_adapters.rest_api.dependencies import ServiceContainer, get_container
from ui_adapters.rest_api.models import FeatureRequestInput, FeatureRequestResponse

router = APIRouter()
_graph_repo = InMemoryGraphRepository()


def _build_handler(container: ServiceContainer) -> FeatureRequestHandler:
    llm = container.llm
    persona_uc = GeneratePersonasUseCase(PersonaGeneratorAdapter(llm))
    scope_uc = GenerateScopeDocumentUseCase(ScopeGeneratorAdapter(llm))
    cq_uc = GenerateCompetencyQuestionsUseCase(
        CompetencyQuestionGeneratorAdapter(llm)
    )
    return FeatureRequestHandler(
        persona_uc=persona_uc,
        scope_uc=scope_uc,
        cq_uc=cq_uc,
        graph_repository=_graph_repo,
    )


@router.post("/api/feature_request", response_model=FeatureRequestResponse)
async def process_feature_request(
    request: FeatureRequestInput,
    container: ServiceContainer = Depends(get_container),
) -> FeatureRequestResponse:
    handler = _build_handler(container)
    result = await handler.handle(
        description=request.description, tenant_id=request.tenant_id
    )
    return FeatureRequestResponse(
        feature_request_id=result.feature_request.id,
        scope_document=result.scope_document.content,
        personas=[p.content for p in result.personas],
        clarifying_questions=[q.question for q in result.clarifying_questions],
    )
