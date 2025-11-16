"""Replit Auth integration adapter for seamless authentication."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from flask import Request

from application.use_cases.create_organization_use_case import CreateOrganizationUseCase
from application.use_cases.user_org.create_user_use_case import (
    CreateUserRequestDTO,
    CreateUserUseCase,
)
from domain.entities import UserRole


@dataclass
class ReplitUserInfo:
    """Replit user information from headers."""

    user_id: str
    username: str
    roles: str

    @classmethod
    def from_request(cls, request: Request) -> Optional["ReplitUserInfo"]:
        """Extract Replit user info from request headers."""
        user_id = request.headers.get("X-Replit-User-Id")
        username = request.headers.get("X-Replit-User-Name")
        roles = request.headers.get("X-Replit-User-Roles", "")

        if user_id and username:
            return cls(user_id=user_id, username=username, roles=roles)
        return None


class ReplitAuthAdapter:
    """Adapter for Replit authentication integration."""

    def __init__(
        self,
        create_user_use_case: CreateUserUseCase,
        create_org_use_case: CreateOrganizationUseCase,
        default_organization_id: str = "replit-users",
        auto_create_users: bool = True,
    ):
        """Initialize Replit Auth adapter.

        Args:
            create_user_use_case: Use case for creating users
            create_org_use_case: Use case for creating organizations
            default_organization_id: Default org for Replit users
            auto_create_users: Whether to auto-create missing users
        """
        self.create_user_use_case = create_user_use_case
        self.create_org_use_case = create_org_use_case
        self.default_organization_id = default_organization_id
        self.auto_create_users = auto_create_users

    def authenticate_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """Authenticate a request using Replit headers.

        Args:
            request: Flask request object

        Returns:
            User context if authenticated, None otherwise
        """
        replit_user = ReplitUserInfo.from_request(request)
        if not replit_user:
            return None

        # Try to get existing user or create new one
        user_context = self._get_or_create_user(replit_user)

        return {
            "user_id": user_context.get("user_id"),
            "username": replit_user.username,
            "replit_user_id": replit_user.user_id,
            "organization_id": user_context.get("organization_id"),
            "tenant_id": user_context.get(
                "organization_id"
            ),  # Organization ID = Tenant ID
            "role": user_context.get("role"),
            "is_authenticated": True,
        }

    def _get_or_create_user(self, replit_user: ReplitUserInfo) -> Dict[str, Any]:
        """Get existing user or create new one for Replit user."""
        # For now, we'll create a simple mapping
        # In production, you'd query your user repository first

        if self.auto_create_users:
            try:
                # Create user request
                create_request = CreateUserRequestDTO(
                    email=f"{replit_user.username}@replit.user",  # Synthetic email
                    name=replit_user.username,
                    password="replit-auth-managed",  # Not used for Replit auth
                    organization_id=self.default_organization_id,
                    role=UserRole.USER.value,
                    created_by_user_id="system",
                )

                response = self.create_user_use_case.execute(create_request)

                if response.success:
                    return {
                        "user_id": response.user.id,
                        "organization_id": response.user.organization_id,
                        "role": response.user.role,
                    }

            except Exception:
                # User might already exist, ignore errors when auto creating
                pass

        # Return default context
        return {
            "user_id": f"replit-{replit_user.user_id}",
            "organization_id": self.default_organization_id,
            "role": UserRole.USER.value,
        }

    def generate_auth_script(self, redirect_url: Optional[str] = None) -> str:
        """Generate Replit Auth script HTML."""
        authed_action = redirect_url or "location.reload()"

        return f"""
        <div id="replit-auth-container">
            <script
                authed="{authed_action}"
                src="https://auth.util.repl.co/script.js">
            </script>
        </div>
        """

    def is_authenticated(self, request: Request) -> bool:
        """Check if request is authenticated via Replit."""
        return ReplitUserInfo.from_request(request) is not None
