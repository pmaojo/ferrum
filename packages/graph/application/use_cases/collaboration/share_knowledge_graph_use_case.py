"""Use case for sharing knowledge graphs with other users or organizations."""

import secrets
import uuid
from datetime import datetime
from typing import List, Optional

from application.exceptions import AuthorizationError, NotFoundError, ValidationError
from application.ports.base import (
    AuthorizationServicePort,
    KnowledgeGraphRepositoryPort,
    NotificationServicePort,
    ShareRepositoryPort,
)
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    ShareKnowledgeGraphRequestDTO,
    ShareKnowledgeGraphResponseDTO,
    ShareLinkDTO,
)
from domain.entities import ShareLink


class ShareKnowledgeGraphUseCase(BaseUseCase):
    """Use case for sharing knowledge graphs."""

    def __init__(
        self,
        kg_repository: KnowledgeGraphRepositoryPort,
        share_repository: ShareRepositoryPort,
        authorization_service: AuthorizationServicePort,
        notification_service: NotificationServicePort,
    ):
        """Initialize the use case with required dependencies."""
        self.kg_repository = kg_repository
        self.share_repository = share_repository
        self.authorization_service = authorization_service
        self.notification_service = notification_service

    def execute(
        self, request: ShareKnowledgeGraphRequestDTO
    ) -> ShareKnowledgeGraphResponseDTO:
        """Execute the share knowledge graph use case."""
        start_time = datetime.now()

        try:
            # Validate input
            self._validate_input(request)

            # Check authorization - user must have admin or share permissions
            if not self.authorization_service.check_permission(
                request.user_id, request.kg_id, "share"
            ):
                raise AuthorizationError(
                    f"User {request.user_id} does not have permission to share knowledge graph {request.kg_id}"
                )

            # Verify knowledge graph exists
            kg = self.kg_repository.get_knowledge_graph_by_id(
                request.kg_id, request.tenant_id
            )
            if not kg:
                raise NotFoundError(
                    f"Knowledge graph with ID {request.kg_id} not found"
                )

            # Validate shared users exist if specific sharing
            if request.share_type == "specific_users" and request.shared_with_user_ids:
                self._validate_shared_users(
                    request.shared_with_user_ids, request.tenant_id
                )

            # Generate share link
            share_link = self._create_share_link(request)

            # Save share link
            created_share_link = self.share_repository.create_share_link(share_link)

            # Send notifications if sharing with specific users
            if request.share_type == "specific_users" and request.shared_with_user_ids:
                self._send_share_notifications(
                    created_share_link, request.shared_with_user_ids, request.message
                )

            # Convert to DTO
            share_link_dto = self._to_share_link_dto(created_share_link)

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            return ShareKnowledgeGraphResponseDTO(
                success=True,
                processing_time_ms=processing_time,
                share_link=share_link_dto,
            )

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            return ShareKnowledgeGraphResponseDTO(
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e),
            )

    def _validate_input(self, request: ShareKnowledgeGraphRequestDTO) -> None:
        """Validate the input request."""
        if not request.kg_id:
            raise ValidationError("Knowledge graph ID is required")

        if not request.tenant_id:
            raise ValidationError("Tenant ID is required")

        if not request.user_id:
            raise ValidationError("User ID is required")

        if request.share_type not in ["public", "organization", "specific_users"]:
            raise ValidationError(f"Invalid share type: {request.share_type}")

        valid_permissions = ["read", "write", "admin"]
        if not request.permissions or not all(
            p in valid_permissions for p in request.permissions
        ):
            raise ValidationError(
                f"Invalid permissions. Must be one or more of: {valid_permissions}"
            )

        if request.share_type == "specific_users" and not request.shared_with_user_ids:
            raise ValidationError(
                "shared_with_user_ids is required when share_type is 'specific_users'"
            )

        if request.expires_at and request.expires_at <= datetime.now():
            raise ValidationError("Expiration date must be in the future")

    def _validate_shared_users(self, user_ids: List[str], tenant_id: str) -> None:
        """Validate that shared users exist and have access to the tenant."""
        # This would typically check against a user repository
        # For now, we'll assume validation is done elsewhere

    def _create_share_link(self, request: ShareKnowledgeGraphRequestDTO) -> ShareLink:
        """Create a share link entity."""
        share_id = str(uuid.uuid4())
        access_token = self._generate_access_token()
        share_url = f"/shared/{share_id}?token={access_token}"

        return ShareLink(
            id=share_id,
            kg_id=request.kg_id,
            tenant_id=request.tenant_id,
            share_type=request.share_type,
            permissions=request.permissions,
            shared_by=request.user_id,
            shared_with_user_ids=request.shared_with_user_ids,
            share_url=share_url,
            access_token=access_token,
            expires_at=request.expires_at,
            is_active=True,
            created_at=datetime.now(),
            last_accessed_at=None,
            access_count=0,
        )

    def _generate_access_token(self) -> str:
        """Generate a secure access token for the share link."""
        return secrets.token_urlsafe(32)

    def _send_share_notifications(
        self, share_link: ShareLink, user_ids: List[str], message: Optional[str]
    ) -> None:
        """Send notifications to users about the shared knowledge graph."""
        for user_id in user_ids:
            self.notification_service.send_share_notification(
                recipient_user_id=user_id,
                share_link=share_link,
                message=message,
            )

    def _to_share_link_dto(self, share_link: ShareLink) -> ShareLinkDTO:
        """Convert ShareLink entity to DTO."""
        return ShareLinkDTO(
            id=share_link.id,
            kg_id=share_link.kg_id,
            tenant_id=share_link.tenant_id,
            share_type=share_link.share_type,
            permissions=share_link.permissions,
            shared_by=share_link.shared_by,
            shared_with_user_ids=share_link.shared_with_user_ids,
            share_url=share_link.share_url,
            access_token=share_link.access_token,
            expires_at=share_link.expires_at,
            is_active=share_link.is_active,
            created_at=share_link.created_at,
            last_accessed_at=share_link.last_accessed_at,
            access_count=share_link.access_count,
        )
