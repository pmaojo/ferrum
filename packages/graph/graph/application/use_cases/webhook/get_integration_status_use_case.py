"""Get integration status use case implementation."""

from datetime import datetime
from typing import List

from application.ports.base import IntegrationStatusPort, WebhookRepositoryPort
from application.ports.security import AuthorizationPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    GetIntegrationStatusRequestDTO,
    IntegrationStatusDTO,
    IntegrationStatusResponseDTO,
)
from domain.exceptions import ValidationError


class GetIntegrationStatusUseCase(
    BaseUseCase[GetIntegrationStatusRequestDTO, IntegrationStatusResponseDTO]
):
    """Use case for getting integration status."""

    def __init__(
        self,
        webhook_repository: WebhookRepositoryPort,
        integration_status_service: IntegrationStatusPort,
        authorization_service: AuthorizationPort,
    ):
        """Initialize the use case.

        Args:
            webhook_repository: Repository for webhook operations
            integration_status_service: Service for checking integration status
            authorization_service: Service for authorization checks
        """
        super().__init__()
        self.webhook_repository = webhook_repository
        self.integration_status_service = integration_status_service
        self.authorization_service = authorization_service

    def execute(
        self, request: GetIntegrationStatusRequestDTO
    ) -> IntegrationStatusResponseDTO:
        """Execute the get integration status use case.

        Args:
            request: Get integration status request DTO

        Returns:
            Integration status response DTO

        Raises:
            ValidationError: When input validation fails
            AuthorizationError: When user lacks permission
        """
        # Validate input
        self._validate_input(request)

        # Check authorization
        self.authorization_service.check_permission(
            user_id=request.user_id,
            resource_type="integration",
            action="read",
            tenant_id=request.tenant_id,
        )

        # Get integration status from service
        integration_statuses = self.integration_status_service.check_integration_status(
            tenant_id=request.tenant_id,
            integration_type=request.integration_type,
        )

        # Convert to DTOs
        integration_dtos = [
            IntegrationStatusDTO(
                integration_type=status["integration_type"],
                integration_id=status["integration_id"],
                name=status["name"],
                status=status["status"],
                last_check_at=status.get("last_check_at"),
                error_message=status.get("error_message"),
                metadata=status.get("metadata", {}),
            )
            for status in integration_statuses
        ]

        # Calculate overall status
        overall_status = self._calculate_overall_status(integration_dtos)

        # Count integrations by status
        total_integrations = len(integration_dtos)
        active_integrations = len([i for i in integration_dtos if i.status == "active"])
        failed_integrations = len([i for i in integration_dtos if i.status == "error"])

        return IntegrationStatusResponseDTO(
            integrations=integration_dtos,
            overall_status=overall_status,
            total_integrations=total_integrations,
            active_integrations=active_integrations,
            failed_integrations=failed_integrations,
            checked_at=datetime.now(),
        )

    def _validate_input(self, request: GetIntegrationStatusRequestDTO) -> None:
        """Validate the get integration status request.

        Args:
            request: Get integration status request DTO

        Raises:
            ValidationError: When validation fails
        """
        # Validate tenant_id
        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError("Tenant ID is required", "tenant_id")

        # Validate user_id
        if not request.user_id or not request.user_id.strip():
            raise ValidationError("User ID is required", "user_id")

        # Validate integration_type if provided
        if request.integration_type is not None:
            valid_types = ["webhook", "api", "external_system"]
            if request.integration_type not in valid_types:
                raise ValidationError(
                    f"Invalid integration type. Must be one of: {', '.join(valid_types)}",
                    "integration_type",
                )

    def _calculate_overall_status(
        self, integrations: List[IntegrationStatusDTO]
    ) -> str:
        """Calculate overall status based on individual integration statuses.

        Args:
            integrations: List of integration status DTOs

        Returns:
            Overall status string
        """
        if not integrations:
            return "healthy"

        # Count statuses
        status_counts = {}
        for integration in integrations:
            status_counts[integration.status] = (
                status_counts.get(integration.status, 0) + 1
            )

        total = len(integrations)
        error_count = status_counts.get("error", 0)
        inactive_count = status_counts.get("inactive", 0)

        # Determine overall status
        if error_count > 0:
            if error_count >= total * 0.5:  # 50% or more failed
                return "critical"
            else:
                return "degraded"
        elif inactive_count > 0:
            if inactive_count >= total * 0.3:  # 30% or more inactive
                return "degraded"
            else:
                return "healthy"
        else:
            return "healthy"
