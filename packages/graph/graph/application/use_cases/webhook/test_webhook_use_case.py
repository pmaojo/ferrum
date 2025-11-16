"""Test webhook use case implementation."""

from datetime import datetime
from typing import Any, Dict

from application.ports.base import WebhookRepositoryPort, WebhookServicePort
from application.ports.security import AuthorizationPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import TestWebhookRequestDTO, WebhookTestResultDTO
from domain.exceptions import NotFoundError, ValidationError


class TestWebhookUseCase(BaseUseCase[TestWebhookRequestDTO, WebhookTestResultDTO]):
    """Use case for testing webhooks."""

    def __init__(
        self,
        webhook_repository: WebhookRepositoryPort,
        webhook_service: WebhookServicePort,
        authorization_service: AuthorizationPort,
    ):
        """Initialize the use case.

        Args:
            webhook_repository: Repository for webhook operations
            webhook_service: Service for webhook HTTP operations
            authorization_service: Service for authorization checks
        """
        super().__init__()
        self.webhook_repository = webhook_repository
        self.webhook_service = webhook_service
        self.authorization_service = authorization_service

    def execute(self, request: TestWebhookRequestDTO) -> WebhookTestResultDTO:
        """Execute the test webhook use case.

        Args:
            request: Test webhook request DTO

        Returns:
            Webhook test result DTO

        Raises:
            ValidationError: When input validation fails
            AuthorizationError: When user lacks permission
            NotFoundError: When webhook is not found
        """
        # Validate input
        self._validate_input(request)

        # Check authorization
        self.authorization_service.check_permission(
            user_id=request.user_id,
            resource_type="webhook",
            action="test",
            tenant_id=request.tenant_id,
        )

        # Get webhook
        webhook = self.webhook_repository.get_by_id(request.webhook_id)
        if not webhook:
            raise NotFoundError(f"Webhook with ID {request.webhook_id} not found")

        # Verify webhook belongs to tenant
        if webhook.tenant_id != request.tenant_id:
            raise NotFoundError(f"Webhook with ID {request.webhook_id} not found")

        # Create test payload
        test_payload = self._create_test_payload(request)

        # Send test event
        try:
            response = self.webhook_service.send_test_event(
                url=webhook.url,
                secret=webhook.secret,
                event_type=request.test_event_type,
                payload=test_payload,
                timeout=30,
            )

            return WebhookTestResultDTO(
                webhook_id=request.webhook_id,
                test_event_type=request.test_event_type,
                success=response.get("success", False),
                response_status=response.get("status_code"),
                response_time_ms=response.get("response_time_ms"),
                error_message=response.get("error_message"),
                tested_at=datetime.now(),
            )

        except Exception as e:
            return WebhookTestResultDTO(
                webhook_id=request.webhook_id,
                test_event_type=request.test_event_type,
                success=False,
                response_status=None,
                response_time_ms=None,
                error_message=str(e),
                tested_at=datetime.now(),
            )

    def _validate_input(self, request: TestWebhookRequestDTO) -> None:
        """Validate the test webhook request.

        Args:
            request: Test webhook request DTO

        Raises:
            ValidationError: When validation fails
        """
        # Validate webhook_id
        if not request.webhook_id or not request.webhook_id.strip():
            raise ValidationError("Webhook ID is required", "webhook_id")

        # Validate test_event_type
        if not request.test_event_type or not request.test_event_type.strip():
            raise ValidationError("Test event type is required", "test_event_type")

        # Validate tenant_id
        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError("Tenant ID is required", "tenant_id")

        # Validate user_id
        if not request.user_id or not request.user_id.strip():
            raise ValidationError("User ID is required", "user_id")

    def _create_test_payload(self, request: TestWebhookRequestDTO) -> Dict[str, Any]:
        """Create test payload for webhook.

        Args:
            request: Test webhook request DTO

        Returns:
            Test payload dictionary
        """
        if request.test_payload:
            return request.test_payload

        # Create default test payload based on event type
        base_payload = {
            "event_type": request.test_event_type,
            "timestamp": datetime.now().isoformat(),
            "tenant_id": request.tenant_id,
            "test": True,
        }

        if request.test_event_type == "test":
            base_payload.update(
                {
                    "message": "This is a test webhook event",
                    "webhook_id": request.webhook_id,
                }
            )
        elif request.test_event_type.startswith("knowledge_graph."):
            base_payload.update(
                {
                    "knowledge_graph": {
                        "id": "test-kg-123",
                        "name": "Test Knowledge Graph",
                        "tenant_id": request.tenant_id,
                    },
                }
            )
        elif request.test_event_type.startswith("ontology."):
            base_payload.update(
                {
                    "ontology": {
                        "id": "test-ontology-123",
                        "name": "Test Ontology",
                        "version": "1.0.0",
                        "tenant_id": request.tenant_id,
                    },
                }
            )
        elif request.test_event_type.startswith(
            "workflow."
        ) or request.test_event_type.startswith("job."):
            base_payload.update(
                {
                    "job": {
                        "id": "test-job-123",
                        "workflow_id": "test-workflow-123",
                        "status": (
                            "completed"
                            if "completed" in request.test_event_type
                            else "failed"
                        ),
                        "tenant_id": request.tenant_id,
                    },
                }
            )
        elif request.test_event_type.startswith("user."):
            base_payload.update(
                {
                    "user": {
                        "id": "test-user-123",
                        "email": "test@example.com",
                        "name": "Test User",
                        "tenant_id": request.tenant_id,
                    },
                }
            )
        elif request.test_event_type.startswith("subscription."):
            base_payload.update(
                {
                    "subscription": {
                        "id": "test-subscription-123",
                        "organization_id": request.tenant_id,
                        "tier": "professional",
                        "status": "active",
                    },
                }
            )

        return base_payload
