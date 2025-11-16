"""Factory for creating authentication adapters based on environment."""

import os
from typing import Union

from flask import Flask

from adapters.external.odoo_integration_adapter import (
    OdooConfig,
    OdooIntegrationAdapter,
)
from adapters.external.supabase_integration_adapter import SupabaseConfig
from application.ports import AuthenticationPort, UserRepositoryPort

from .flask_jwt_auth import FlaskJWTMiddleware
from .flask_replit_auth import ReplitAuthMiddleware
from .integrated_auth_service import IntegratedAuthService
from .jwt_auth_adapter import JWTAuthAdapter, JWTConfig
from .replit_auth_adapter import ReplitAuthAdapter
from .supabase_auth_adapter import SupabaseAuthAdapter


class AuthenticationFactory:
    """Factory for creating authentication adapters."""

    @staticmethod
    def create_auth_middleware(
        app: Flask, user_repository: UserRepositoryPort, auth_type: str = None
    ) -> Union[ReplitAuthMiddleware, FlaskJWTMiddleware]:
        """Create authentication middleware based on environment."""

        if auth_type is None:
            # Auto-detect based on environment
            auth_type = "replit" if os.getenv("REPLIT") else "jwt"

        if auth_type == "replit":
            # Use Replit Auth for development on Replit
            auth_adapter = ReplitAuthAdapter(
                create_user_use_case=None,  # Inject proper dependency
                create_org_use_case=None,  # Inject proper dependency
            )
            return ReplitAuthMiddleware(app, auth_adapter)

        elif auth_type == "jwt":
            # Use JWT Auth for production
            secret_key = os.getenv("JWT_SECRET_KEY")
            if not secret_key:
                raise ValueError(
                    "JWT_SECRET_KEY environment variable is required for JWT auth"
                )

            jwt_config = JWTConfig(
                secret_key=secret_key,
                access_token_expire_minutes=int(
                    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
                ),
                refresh_token_expire_days=int(
                    os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
                ),
            )

            jwt_adapter = JWTAuthAdapter(jwt_config)
            return FlaskJWTMiddleware(app, jwt_adapter, user_repository)

        else:
            raise ValueError(f"Unsupported auth type: {auth_type}")

    @staticmethod
    def create_auth_adapter(auth_type: str = "jwt") -> AuthenticationPort:
        """Create authentication adapter based on configuration."""
        if auth_type.lower() == "supabase":
            return SupabaseAuthAdapter()
        elif auth_type.lower() == "jwt":
            return JWTAuthAdapter()
        elif auth_type.lower() == "integrated":
            # Note: IntegratedAuthService is not a direct AuthenticationPort
            # You might need to create a wrapper or use composition
            return SupabaseAuthAdapter()  # Use Supabase as base for integrated
        else:
            raise ValueError(f"Unsupported auth type: {auth_type}")

    @staticmethod
    def create_integrated_service(create_user_use_case):
        """Create integrated authentication service with full ERP integration."""
        supabase_config = SupabaseConfig(
            url=os.getenv("SUPABASE_URL", ""),
            anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
            service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            project_ref=os.getenv("SUPABASE_PROJECT_REF", ""),
        )
        odoo_config = OdooConfig(
            url=os.getenv("ODOO_URL", ""),
            database=os.getenv("ODOO_DATABASE", ""),
            username=os.getenv("ODOO_USERNAME", ""),
            password=os.getenv("ODOO_PASSWORD", ""),
            api_key=os.getenv("ODOO_API_KEY"),
        )
        erp_adapter = OdooIntegrationAdapter(odoo_config)
        return IntegratedAuthService(
            create_user_use_case,
            supabase_config,
            odoo_config,
            erp_adapter,
        )

    @staticmethod
    def is_production() -> bool:
        """Check if running in production environment."""
        return os.getenv("ENVIRONMENT") == "production" or not os.getenv("REPLIT")
