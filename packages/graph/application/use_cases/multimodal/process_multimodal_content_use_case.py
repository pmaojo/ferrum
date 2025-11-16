"""Use case for processing multimodal content in knowledge graphs."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from application.exceptions import AuthorizationError, ValidationError
from application.ports import (
    AuditLoggingPort,
    AuthorizationPort,
    EmbeddingCachePort,
    MultimodalProcessingPort,
)
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO
from domain.entities import MultimodalContentType

logger = logging.getLogger(__name__)


@dataclass
class ProcessMultimodalContentRequestDTO:
    """Request DTO for processing multimodal content."""

    tenant_id: str
    user_id: str
    kg_id: str
    content_path: str
    content_type: str  # Will be converted to MultimodalContentType
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MultimodalEntityDTO:
    """DTO for multimodal entity response."""

    id: str
    content_type: str
    content_path: str
    extracted_text: Optional[str]
    processing_status: str
    relationships_count: int
    embeddings_count: int


@dataclass
class ProcessMultimodalContentResponseDTO(BaseResponseDTO):
    """Response DTO for processing multimodal content."""

    entity: Optional[MultimodalEntityDTO] = None


class ProcessMultimodalContentUseCase(
    BaseUseCase[ProcessMultimodalContentRequestDTO, ProcessMultimodalContentResponseDTO]
):
    """Use case for processing multimodal content."""

    def __init__(
        self,
        multimodal_processing_port: MultimodalProcessingPort,
        embedding_cache_port: EmbeddingCachePort,
        authorization_port: AuthorizationPort,
        audit_logging_port: AuditLoggingPort,
    ):
        """Initialize the multimodal content processing use case."""
        super().__init__()
        self.multimodal_port = multimodal_processing_port
        self.cache_port = embedding_cache_port
        self.authz = authorization_port
        self.audit = audit_logging_port

    async def _execute_internal(
        self, request: ProcessMultimodalContentRequestDTO
    ) -> ProcessMultimodalContentResponseDTO:
        """Execute multimodal content processing operation."""
        logger.info(
            f"Starting multimodal content processing for kg_id={request.kg_id}, content_type={request.content_type}"
        )

        # Check authorization
        if not await self.authz.check_permission(
            request.user_id, request.kg_id, "write"
        ):
            raise AuthorizationError(
                message=f"User {request.user_id} lacks write permission for knowledge graph {request.kg_id}",
                user_id=request.user_id,
                resource_type="knowledge_graph",
                resource_id=request.kg_id,
                required_permission="write",
            )

        # Validate content type
        try:
            content_type = MultimodalContentType(request.content_type.lower())
        except ValueError:
            raise ValidationError(
                message=f"Invalid content type: {request.content_type}",
                param="content_type",
            )

        try:
            # Process the multimodal content
            entity = await self.multimodal_port.process_content(
                content_path=request.content_path,
                content_type=content_type,
                tenant_id=request.tenant_id,
                kg_id=request.kg_id,
                metadata=request.metadata,
            )

            # Log the action
            await self.audit.log_action(
                tenant_id=request.tenant_id,
                action="process_multimodal_content",
                resource_type="multimodal_entity",
                resource_id=entity.id,
                details={
                    "content_type": request.content_type,
                    "content_path": request.content_path,
                    "kg_id": request.kg_id,
                },
                user_id=request.user_id,
            )

            # Convert to DTO
            entity_dto = MultimodalEntityDTO(
                id=entity.id,
                content_type=entity.content_type.value,
                content_path=entity.content_path,
                extracted_text=entity.extracted_text,
                processing_status=entity.processing_status,
                relationships_count=len(entity.relationships),
                embeddings_count=len(entity.embeddings),
            )

            return ProcessMultimodalContentResponseDTO(
                success=True,
                entity=entity_dto,
            )

        except Exception as e:
            logger.error(f"Failed to process multimodal content: {str(e)}")
            raise ValidationError(
                f"Multimodal content processing failed: {str(e)}"
            ) from e
