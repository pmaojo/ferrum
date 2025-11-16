"""User registration service with external integrations."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from application.exceptions import ApplicationError
from application.ports.erp import ERPPort
from application.use_cases.dto import CreateUserRequestDTO
from application.use_cases.user_org.create_user_use_case import CreateUserUseCase

ERROR_CREATE_USER_FAILED = "REGISTRATION_CREATE_USER_ERROR"
ERROR_REGISTRATION_FAILED = "REGISTRATION_ERROR"


@dataclass
class RegistrationRequest:
    """User registration request."""

    email: str
    name: str
    password: str
    organization_name: str
    subscription_tier: str = "free"


class UserRegistrationService:
    """Service for handling user registration with external integrations."""

    def __init__(
        self,
        create_user_use_case: CreateUserUseCase,
        erp_adapter: Optional[ERPPort] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize registration service."""
        self.create_user_use_case = create_user_use_case
        self.erp_adapter = erp_adapter
        self.logger = logger or logging.getLogger(__name__)

    async def register_user(self, request: RegistrationRequest) -> Dict[str, Any]:
        """Register a new user with optional external system integration."""
        try:
            # Create organization first (simplified - you'd need to implement this)
            org_id = await self._create_organization(request.organization_name)

            # Create user
            user_request = CreateUserRequestDTO(
                email=request.email,
                name=request.name,
                password=request.password,
                organization_id=org_id,
                role="admin",  # First user becomes admin
                created_by_user_id="system",
            )

            user_response = await self.create_user_use_case.execute(
                request=user_request
            )

            if not user_response.success:
                raise ApplicationError(
                    f"Failed to create user: {user_response.error_message}",
                    error_code=ERROR_CREATE_USER_FAILED,
                )

            # Sync to external systems if configured
            external_data = {}
            if self.erp_adapter:
                try:
                    customer_id = await self.erp_adapter.create_customer(
                        {
                            "name": request.name,
                            "email": request.email,
                            "organization": request.organization_name,
                            "tier": request.subscription_tier,
                        }
                    )
                    external_data = {"erp_customer_id": customer_id}
                except Exception as e:
                    # Log error but don't fail registration
                    self.logger.warning("Failed to sync to ERP: %s", str(e))

            return {
                "success": True,
                "user": user_response.user,
                "external_integrations": external_data,
            }

        except Exception as e:
            raise ApplicationError(
                f"Registration failed: {str(e)}",
                error_code=ERROR_REGISTRATION_FAILED,
            )

    async def _create_organization(self, name: str) -> str:
        """Create organization (placeholder - implement based on your needs)."""
        # This would use your CreateOrganizationUseCase
        import uuid

        return str(uuid.uuid4())
