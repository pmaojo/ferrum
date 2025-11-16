"""Create webhook use case implementation."""

import secrets
import uuid
from datetime import datetime
from urllib.parse import urlparse

from application.ports.base import WebhookRepositoryPort
from application.ports.security import AuthorizationPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import CreateWebhookRequestDTO, WebhookDTO
from domain.entities import Webhook, WebhookStatus
from domain.exceptions import ValidationError


class CreateWebhookUseCase(BaseUseCase[CreateWebhookRequestDTO, WebhookDTO]):
    """Use case for creating webhooks."""

    # Valid webhook events
    VALID_WEBHOOK_EVENTS = [
        "knowledge_graph.created",
        "knowledge_graph.updated",
        "knowledge_graph.deleted",
        "ontology.created",
        "ontology.updated",
        "user.created",
        "user.updated",
        "workflow.completed",
        "workflow.failed",
        "job.completed",
        "job.failed",
        "subscription.created",
        "subscription.updated",
        "subscription.cancelled",
    ]

    def __init__(
        self,
        webhook_repository: WebhookRepositoryPort,
        authorization_service: AuthorizationPort,
    ):
        """Initialize the use case.

        Args:
            webhook_repository: Repository for webhook operations
            authorization_service: Service for authorization checks
        """
        super().__init__()
        self.webhook_repository = webhook_repository
        self.authorization_service = authorization_service

    async def _execute_internal(self, request: CreateWebhookRequestDTO) -> WebhookDTO:
        """Execute the create webhook use case internal logic.

        Args:
            request: Create webhook request DTO

        Returns:
            Created webhook DTO

        Raises:
            ValidationError: When input validation fails
            AuthorizationError: When user lacks permission
        """

        # Check authorization
        self.authorization_service.check_permission(
            user_id=request.user_id,
            resource_type="webhook",
            action="create",
            tenant_id=request.tenant_id,
        )

        # Generate webhook secret
        secret = self._generate_webhook_secret()

        # Create webhook entity
        webhook = Webhook(
            id=str(uuid.uuid4()),
            tenant_id=request.tenant_id,
            url=request.url,
            events=request.events,
            secret=secret,
            status=(
                WebhookStatus.ACTIVE if request.is_active else WebhookStatus.INACTIVE
            ),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Save to repository
        created_webhook = self.webhook_repository.create(webhook)

        # Return DTO with secret (only returned on creation)
        return WebhookDTO(
            id=created_webhook.id,
            name=request.name,
            url=created_webhook.url,
            events=created_webhook.events,
            tenant_id=created_webhook.tenant_id,
            secret=created_webhook.secret,  # Include secret only in creation response
            description=request.description,
            is_active=created_webhook.status == WebhookStatus.ACTIVE,
            created_at=created_webhook.created_at,
            updated_at=created_webhook.updated_at,
            last_triggered_at=None,
            success_count=0,
            failure_count=0,
        )

    def _validate_request_internal(self, request: CreateWebhookRequestDTO) -> None:
        """Validate the create webhook request.

        Args:
            request: Create webhook request DTO

        Raises:
            ValidationError: When validation fails
        """
        # Validate name
        if not request.name or not request.name.strip():
            raise ValidationError("Webhook name is required", "name")

        if len(request.name) > 255:
            raise ValidationError("Webhook name must be 255 characters or less", "name")

        # Validate URL
        if not request.url or not request.url.strip():
            raise ValidationError("Webhook URL is required", "url")

        # Validate URL format
        try:
            parsed_url = urlparse(request.url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValidationError("Invalid webhook URL format", "url")

            if parsed_url.scheme not in ["http", "https"]:
                raise ValidationError("Webhook URL must use HTTP or HTTPS", "url")
        except Exception:
            raise ValidationError("Invalid webhook URL format", "url")

        # Validate events
        if not request.events:
            raise ValidationError("At least one webhook event is required", "events")

        invalid_events = [
            event for event in request.events if event not in self.VALID_WEBHOOK_EVENTS
        ]
        if invalid_events:
            raise ValidationError(
                f"Invalid webhook events: {', '.join(invalid_events)}. "
                f"Valid events are: {', '.join(self.VALID_WEBHOOK_EVENTS)}",
                "events",
            )

        # Validate tenant_id
        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError("Tenant ID is required", "tenant_id")

        # Validate user_id
        if not request.user_id or not request.user_id.strip():
            raise ValidationError("User ID is required", "user_id")

    def _generate_webhook_secret(self) -> str:
        """Generate a secure webhook secret.

        Returns:
            Generated webhook secret
        """
        return secrets.token_hex(32)
