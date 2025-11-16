"""Manage API keys use case implementation."""

import secrets
import uuid
from datetime import datetime

from application.ports.security import APIKeyManagementPort, AuthorizationPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    APIKeyDTO,
    APIKeyManagementResponseDTO,
    ManageAPIKeysRequestDTO,
)
from domain.exceptions import NotFoundError, ValidationError


class ManageAPIKeysUseCase(
    BaseUseCase[ManageAPIKeysRequestDTO, APIKeyManagementResponseDTO]
):
    """Use case for managing API keys."""

    # Valid actions
    VALID_ACTIONS = ["create", "update", "delete", "list", "rotate"]

    # Valid scopes
    VALID_SCOPES = [
        "knowledge_graph:read",
        "knowledge_graph:write",
        "ontology:read",
        "ontology:write",
        "user:read",
        "user:write",
        "webhook:read",
        "webhook:write",
        "analytics:read",
        "search:read",
        "workflow:read",
        "workflow:write",
        "admin:read",
        "admin:write",
    ]

    def __init__(
        self,
        api_key_management_service: APIKeyManagementPort,
        authorization_service: AuthorizationPort,
    ):
        """Initialize the use case.

        Args:
            api_key_management_service: Service for API key management
            authorization_service: Service for authorization checks
        """
        super().__init__()
        self.api_key_management_service = api_key_management_service
        self.authorization_service = authorization_service

    def execute(self, request: ManageAPIKeysRequestDTO) -> APIKeyManagementResponseDTO:
        """Execute the manage API keys use case.

        Args:
            request: Manage API keys request DTO

        Returns:
            API key management response DTO

        Raises:
            ValidationError: When input validation fails
            AuthorizationError: When user lacks permission
            NotFoundError: When API key is not found
        """
        # Validate input
        self._validate_input(request)

        # Check authorization
        self.authorization_service.check_permission(
            user_id=request.user_id,
            resource_type="api_key",
            action=request.action,
            tenant_id=request.tenant_id,
        )

        # Execute action
        if request.action == "create":
            return self._create_api_key(request)
        elif request.action == "update":
            return self._update_api_key(request)
        elif request.action == "delete":
            return self._delete_api_key(request)
        elif request.action == "list":
            return self._list_api_keys(request)
        elif request.action == "rotate":
            return self._rotate_api_key(request)
        else:
            raise ValidationError(f"Unsupported action: {request.action}", "action")

    def _create_api_key(
        self, request: ManageAPIKeysRequestDTO
    ) -> APIKeyManagementResponseDTO:
        """Create a new API key.

        Args:
            request: Manage API keys request DTO

        Returns:
            API key management response DTO
        """
        if not request.name:
            raise ValidationError("API key name is required for creation", "name")

        if not request.scopes:
            raise ValidationError("API key scopes are required for creation", "scopes")

        # Generate API key
        full_key = self._generate_api_key()
        key_prefix = full_key[:8]

        # Set expiration if provided
        expires_at = request.expires_at
        if expires_at and expires_at <= datetime.now():
            raise ValidationError("Expiration date must be in the future", "expires_at")

        # Create API key
        api_key_data = {
            "id": str(uuid.uuid4()),
            "name": request.name,
            "tenant_id": request.tenant_id,
            "scopes": request.scopes,
            "key_prefix": key_prefix,
            "full_key": full_key,
            "expires_at": expires_at,
            "rate_limit": request.rate_limit,
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "last_used_at": None,
            "usage_count": 0,
        }

        created_key = self.api_key_management_service.create_api_key(
            tenant_id=request.tenant_id,
            api_key_data=api_key_data,
        )

        api_key_dto = APIKeyDTO(
            id=created_key["id"],
            name=created_key["name"],
            tenant_id=created_key["tenant_id"],
            scopes=created_key["scopes"],
            key_prefix=created_key["key_prefix"],
            expires_at=created_key.get("expires_at"),
            rate_limit=created_key.get("rate_limit"),
            is_active=created_key["is_active"],
            created_at=created_key["created_at"],
            updated_at=created_key["updated_at"],
            last_used_at=created_key.get("last_used_at"),
            usage_count=created_key["usage_count"],
        )

        return APIKeyManagementResponseDTO(
            action="create",
            success=True,
            api_key=api_key_dto,
            full_key=full_key,  # Only returned on creation
            message="API key created successfully",
        )

    def _update_api_key(
        self, request: ManageAPIKeysRequestDTO
    ) -> APIKeyManagementResponseDTO:
        """Update an existing API key.

        Args:
            request: Manage API keys request DTO

        Returns:
            API key management response DTO
        """
        if not request.api_key_id:
            raise ValidationError("API key ID is required for update", "api_key_id")

        # Get existing API key
        existing_key = self.api_key_management_service.get_api_key(
            tenant_id=request.tenant_id,
            api_key_id=request.api_key_id,
        )

        if not existing_key:
            raise NotFoundError(f"API key with ID {request.api_key_id} not found")

        # Prepare update data
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.scopes is not None:
            update_data["scopes"] = request.scopes
        if request.expires_at is not None:
            if request.expires_at <= datetime.now():
                raise ValidationError(
                    "Expiration date must be in the future", "expires_at"
                )
            update_data["expires_at"] = request.expires_at
        if request.rate_limit is not None:
            update_data["rate_limit"] = request.rate_limit

        update_data["updated_at"] = datetime.now()

        # Update API key
        updated_key = self.api_key_management_service.update_api_key(
            tenant_id=request.tenant_id,
            api_key_id=request.api_key_id,
            update_data=update_data,
        )

        api_key_dto = APIKeyDTO(
            id=updated_key["id"],
            name=updated_key["name"],
            tenant_id=updated_key["tenant_id"],
            scopes=updated_key["scopes"],
            key_prefix=updated_key["key_prefix"],
            expires_at=updated_key.get("expires_at"),
            rate_limit=updated_key.get("rate_limit"),
            is_active=updated_key["is_active"],
            created_at=updated_key["created_at"],
            updated_at=updated_key["updated_at"],
            last_used_at=updated_key.get("last_used_at"),
            usage_count=updated_key["usage_count"],
        )

        return APIKeyManagementResponseDTO(
            action="update",
            success=True,
            api_key=api_key_dto,
            message="API key updated successfully",
        )

    def _delete_api_key(
        self, request: ManageAPIKeysRequestDTO
    ) -> APIKeyManagementResponseDTO:
        """Delete an API key.

        Args:
            request: Manage API keys request DTO

        Returns:
            API key management response DTO
        """
        if not request.api_key_id:
            raise ValidationError("API key ID is required for deletion", "api_key_id")

        # Check if API key exists
        existing_key = self.api_key_management_service.get_api_key(
            tenant_id=request.tenant_id,
            api_key_id=request.api_key_id,
        )

        if not existing_key:
            raise NotFoundError(f"API key with ID {request.api_key_id} not found")

        # Delete API key
        success = self.api_key_management_service.delete_api_key(
            tenant_id=request.tenant_id,
            api_key_id=request.api_key_id,
        )

        return APIKeyManagementResponseDTO(
            action="delete",
            success=success,
            message=(
                "API key deleted successfully"
                if success
                else "Failed to delete API key"
            ),
        )

    def _list_api_keys(
        self, request: ManageAPIKeysRequestDTO
    ) -> APIKeyManagementResponseDTO:
        """List API keys for a tenant.

        Args:
            request: Manage API keys request DTO

        Returns:
            API key management response DTO
        """
        # Get API keys
        api_keys_data = self.api_key_management_service.list_api_keys(
            tenant_id=request.tenant_id,
        )

        api_keys = [
            APIKeyDTO(
                id=key["id"],
                name=key["name"],
                tenant_id=key["tenant_id"],
                scopes=key["scopes"],
                key_prefix=key["key_prefix"],
                expires_at=key.get("expires_at"),
                rate_limit=key.get("rate_limit"),
                is_active=key["is_active"],
                created_at=key["created_at"],
                updated_at=key["updated_at"],
                last_used_at=key.get("last_used_at"),
                usage_count=key["usage_count"],
            )
            for key in api_keys_data
        ]

        return APIKeyManagementResponseDTO(
            action="list",
            success=True,
            api_keys=api_keys,
            message=f"Found {len(api_keys)} API keys",
        )

    def _rotate_api_key(
        self, request: ManageAPIKeysRequestDTO
    ) -> APIKeyManagementResponseDTO:
        """Rotate an API key (generate new key value).

        Args:
            request: Manage API keys request DTO

        Returns:
            API key management response DTO
        """
        if not request.api_key_id:
            raise ValidationError("API key ID is required for rotation", "api_key_id")

        # Check if API key exists
        existing_key = self.api_key_management_service.get_api_key(
            tenant_id=request.tenant_id,
            api_key_id=request.api_key_id,
        )

        if not existing_key:
            raise NotFoundError(f"API key with ID {request.api_key_id} not found")

        # Generate new API key
        new_full_key = self._generate_api_key()
        new_key_prefix = new_full_key[:8]

        # Update API key with new values
        update_data = {
            "key_prefix": new_key_prefix,
            "full_key": new_full_key,
            "updated_at": datetime.now(),
        }

        updated_key = self.api_key_management_service.update_api_key(
            tenant_id=request.tenant_id,
            api_key_id=request.api_key_id,
            update_data=update_data,
        )

        api_key_dto = APIKeyDTO(
            id=updated_key["id"],
            name=updated_key["name"],
            tenant_id=updated_key["tenant_id"],
            scopes=updated_key["scopes"],
            key_prefix=updated_key["key_prefix"],
            expires_at=updated_key.get("expires_at"),
            rate_limit=updated_key.get("rate_limit"),
            is_active=updated_key["is_active"],
            created_at=updated_key["created_at"],
            updated_at=updated_key["updated_at"],
            last_used_at=updated_key.get("last_used_at"),
            usage_count=updated_key["usage_count"],
        )

        return APIKeyManagementResponseDTO(
            action="rotate",
            success=True,
            api_key=api_key_dto,
            full_key=new_full_key,  # Return new key value
            message="API key rotated successfully",
        )

    def _validate_input(self, request: ManageAPIKeysRequestDTO) -> None:
        """Validate the manage API keys request.

        Args:
            request: Manage API keys request DTO

        Raises:
            ValidationError: When validation fails
        """
        # Validate action
        if not request.action or request.action not in self.VALID_ACTIONS:
            raise ValidationError(
                f"Invalid action. Must be one of: {', '.join(self.VALID_ACTIONS)}",
                "action",
            )

        # Validate tenant_id
        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError("Tenant ID is required", "tenant_id")

        # Validate user_id
        if not request.user_id or not request.user_id.strip():
            raise ValidationError("User ID is required", "user_id")

        # Validate scopes if provided
        if request.scopes is not None:
            invalid_scopes = [
                scope for scope in request.scopes if scope not in self.VALID_SCOPES
            ]
            if invalid_scopes:
                raise ValidationError(
                    f"Invalid scopes: {', '.join(invalid_scopes)}. "
                    f"Valid scopes are: {', '.join(self.VALID_SCOPES)}",
                    "scopes",
                )

        # Validate rate_limit if provided
        if request.rate_limit is not None and request.rate_limit <= 0:
            raise ValidationError("Rate limit must be a positive integer", "rate_limit")

    def _generate_api_key(self) -> str:
        """Generate a secure API key.

        Returns:
            Generated API key string
        """
        # Generate a 32-byte random key and encode as hex
        return f"ak_{secrets.token_hex(32)}"
