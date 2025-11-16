"""REST API routes for cross-modal retrieval."""

from fastapi import APIRouter, Depends, HTTPException

from ui_adapters.rest_api.dependencies import ServiceContainer, get_container
from ui_adapters.rest_api.models import CrossModalRetrievalRequest
from application.use_cases.multimodal.cross_modal_retrieval_use_case import (
    CrossModalRetrievalUseCase,
    CrossModalRetrievalRequestDTO,
)


router = APIRouter(prefix="/multimodal", tags=["multimodal"])


@router.post("/retrieve")
async def cross_modal_retrieve(
    request: CrossModalRetrievalRequest,
    container: ServiceContainer = Depends(get_container),
):
    if not getattr(container, "cross_modal_port", None):
        raise HTTPException(status_code=501, detail="Cross modal retrieval not configured")

    use_case = CrossModalRetrievalUseCase(
        retrieval_port=container.cross_modal_port,
        embedding_cache_port=container.image_embedding_adapter,  # placeholder
        authorization_port=None,
    )

    dto = CrossModalRetrievalRequestDTO(
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        kg_id=request.kg_id,
        text_query=request.text_query,
        image_path=request.image_path,
        audio_path=request.audio_path,
        limit=request.limit,
        threshold=request.threshold,
    )

    return await use_case.execute(dto)
