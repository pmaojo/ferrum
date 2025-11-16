"""Flask middleware for Replit authentication."""

from functools import wraps
from typing import Callable

from flask import Flask, g, jsonify, request

from .replit_auth_adapter import ReplitAuthAdapter


class ReplitAuthMiddleware:
    """Flask middleware for Replit authentication."""

    def __init__(self, app: Flask, auth_adapter: ReplitAuthAdapter):
        """Initialize middleware."""
        self.app = app
        self.auth_adapter = auth_adapter

        # Register before_request handler
        app.before_request(self.before_request)

    def before_request(self):
        """Process authentication before each request."""
        # Skip auth for health checks and public endpoints
        if request.endpoint in ["health", "docs", "openapi"]:
            return

        # Authenticate request
        user_context = self.auth_adapter.authenticate_request(request)

        if user_context:
            g.user = user_context
        else:
            g.user = None

    def require_auth(self, f: Callable) -> Callable:
        """Decorator to require authentication."""

        @wraps(f)
        def decorated_function(*args, **kwargs):
            if (
                not hasattr(g, "user")
                or not g.user
                or not g.user.get("is_authenticated")
            ):
                return (
                    jsonify(
                        {
                            "error": "Authentication required",
                            "message": "Please authenticate with Replit Auth",
                        }
                    ),
                    401,
                )
            return f(*args, **kwargs)

        return decorated_function

    def require_role(self, required_role: str):
        """Decorator to require specific role."""

        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if (
                    not hasattr(g, "user")
                    or not g.user
                    or not g.user.get("is_authenticated")
                ):
                    return jsonify({"error": "Authentication required"}), 401

                user_role = g.user.get("role", "user")
                if user_role != required_role and user_role != "admin":
                    return jsonify({"error": "Insufficient permissions"}), 403

                return f(*args, **kwargs)

            return decorated_function

        return decorator


def setup_replit_auth(app: Flask) -> ReplitAuthMiddleware:
    """Setup Replit Auth for Flask app."""

    # You'll need to inject these dependencies properly. This is a simplified
    # example that constructs the adapter with placeholder dependencies.
    auth_adapter = ReplitAuthAdapter(
        create_user_use_case=None,  # Inject proper dependency
        create_org_use_case=None,  # Inject proper dependency
    )

    return ReplitAuthMiddleware(app, auth_adapter)
