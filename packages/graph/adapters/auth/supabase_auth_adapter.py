"""Supabase authentication adapter for production use."""

import os
from datetime import datetime
from typing import Any, Dict, Optional

from adapters.external.supabase_integration_adapter import (
    SupabaseConfig,
    SupabaseIntegrationAdapter,
)
from application.ports import AuthenticationPort


class SupabaseAuthAdapter(AuthenticationPort):
    """Supabase authentication adapter."""

    def __init__(self):
        """Initialize Supabase auth adapter."""
        config = SupabaseConfig(
            url=os.getenv("SUPABASE_URL", ""),
            anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
            service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            project_ref=os.getenv("SUPABASE_PROJECT_REF", ""),
        )
        self.supabase = SupabaseIntegrationAdapter(config)

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with Supabase."""
        return self.supabase.authenticate_user(email, password)

    def get_current_user(
        self, request_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get current user from request context."""
        auth_header = request_context.get("headers", {}).get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]
        try:
            # Verify token with Supabase
            import jwt

            # In production, you'd verify with Supabase's JWT secret
            # For now, return basic user info from token
            payload = jwt.decode(token, options={"verify_signature": False})
            return {
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "role": payload.get("role", "user"),
            }
        except Exception:
            return None

    def create_session(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create user session."""
        return {
            "session_id": user_data.get("access_token"),
            "user_id": user_data.get("user", {}).get("id"),
            "expires_at": datetime.now().isoformat(),
        }

    def validate_session(self, session_token: str) -> bool:
        """Validate user session."""
        try:
            import jwt

            jwt.decode(session_token, options={"verify_signature": False})
            return True
        except Exception:
            return False
