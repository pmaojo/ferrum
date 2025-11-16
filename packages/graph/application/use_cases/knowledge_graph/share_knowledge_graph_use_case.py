"""Use case for creating sharing links for knowledge graphs."""

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from application.exceptions import (
    ApplicationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from application.ports import SharingRepositoryPort, TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, TenantScopedRequestDTO
from application.use_cases.knowledge_graph.create_knowledge_graph_use_case import (
    KnowledgeGraphRepositoryPort,
)
from application.use_cases.knowledge_graph.update_knowledge_graph_use_case import (
    AuthorizationServicePort,
)
from domain.entities import SharingLink


@dataclass
class SharingLinkDTO:
    """Data transfer object for sharing links."""

    id: str
    kg_id: str
    token: str
    permissions: List[str]
    expires_at: Optional[datetime]
    tenant_id: str
    created_by: str


@dataclass
class ShareKnowledgeGraphRequest(TenantScopedRequestDTO):
    """Request to create a sharing link for a knowledge graph."""

    kg_id: str
    permissions: List[str]
    expiry_days: Optional[int] = None


@dataclass
class ShareKnowledgeGraphResponse(BaseResponseDTO):
    """Response from sharing a knowledge graph."""

    sharing_link: Optional[SharingLinkDTO] = None


class ShareKnowledgeGraphUseCase(
    BaseUseCase[ShareKnowledgeGraphRequest, ShareKnowledgeGraphResponse]
):
    """Create sharing links with token generation and authorization."""

    def __init__(
        self,
        kg_repository: KnowledgeGraphRepositoryPort,
        sharing_repository: SharingRepositoryPort,
        authorization_service: AuthorizationServicePort,
        tracer: TracingPort,
    ) -> None:
        super().__init__()
        self.kg_repository = kg_repository
        self.sharing_repository = sharing_repository
        self.authorization_service = authorization_service
        self.tracer = tracer

    def _validate_request_internal(self, request: ShareKnowledgeGraphRequest) -> None:
        if not request.kg_id or not request.kg_id.strip():
            raise ValidationError(
                message="Knowledge graph ID is required and cannot be empty",
                field="kg_id",
            )
        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError(
                message="Tenant ID is required and cannot be empty",
                field="tenant_id",
            )
        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty",
                field="user_id",
            )
        if not request.permissions or not isinstance(request.permissions, list):
            raise ValidationError(
                message="Permissions must be a non-empty list",
                field="permissions",
            )
        if request.expiry_days is not None and request.expiry_days <= 0:
            raise ValidationError(
                message="expiry_days must be positive",
                field="expiry_days",
            )

    async def _execute_internal(
        self, request: ShareKnowledgeGraphRequest
    ) -> ShareKnowledgeGraphResponse:
        start_time = datetime.utcnow()
        with self.tracer.start_span(
            name="share_knowledge_graph",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            kg_id=request.kg_id,
        ):
            try:
                self.authorization_service.check_permission(
                    user_id=request.user_id,
                    resource_id=request.kg_id,
                    permission="share",
                )

                kg = self.kg_repository.get_by_id(request.kg_id, request.tenant_id)
                if not kg:
                    raise NotFoundError(
                        message=f"Knowledge graph with ID '{request.kg_id}' not found",
                        resource_type="knowledge_graph",
                        resource_id=request.kg_id,
                    )

                token = secrets.token_urlsafe(32)
                expires_at = (
                    datetime.utcnow() + timedelta(days=request.expiry_days)
                    if request.expiry_days
                    else None
                )

                link = SharingLink.create(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    token=token,
                    permissions=request.permissions,
                    expires_at=expires_at,
                    created_by=request.user_id,
                )

                created = self.sharing_repository.create(link)

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="sharing_link_created",
                    value=1,
                    tenant_id=request.tenant_id,
                )

                dto = SharingLinkDTO(
                    id=created.id,
                    kg_id=created.kg_id,
                    token=created.token,
                    permissions=created.permissions,
                    expires_at=created.expires_at,
                    tenant_id=created.tenant_id,
                    created_by=created.created_by,
                )

                return ShareKnowledgeGraphResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    sharing_link=dto,
                )

            except Exception as e:
                self.tracer.record_metric(
                    name="sharing_link_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                if isinstance(e, (ValidationError, AuthorizationError, NotFoundError)):
                    return ShareKnowledgeGraphResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                raise ApplicationError(
                    message=f"Failed to share knowledge graph: {str(e)}",
                    error_code="SHARE_KG_FAILED",
                ) from e
