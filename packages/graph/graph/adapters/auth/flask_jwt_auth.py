"""Flask middleware for JWT authentication."""

from functools import wraps
from typing import Callable

from flask import Flask, g, jsonify, request

from application.ports import UserRepositoryPort

from .jwt_auth_adapter import JWTAuthAdapter


class FlaskJWTMiddleware:
    """Flask middleware for JWT authentication."""

    def __init__(
        self,
        app: Flask,
        jwt_adapter: JWTAuthAdapter,
        user_repository: UserRepositoryPort,
    ):
        """Initialize middleware."""
        self.app = app
        self.jwt_adapter = jwt_adapter
        self.user_repository = user_repository

        # Register before_request handler
        app.before_request(self.before_request)

        # Register auth routes
        self.register_auth_routes(app)

    def before_request(self):
        """Process authentication before each request."""
        # Skip auth for public endpoints
        public_endpoints = [
            "auth.login",
            "auth.register",
            "health",
            "docs",
            "openapi",
        ]
        if request.endpoint in public_endpoints:
            return

        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            g.user = None
            return

        token = auth_header.split(" ")[1]

        try:
            payload = self.jwt_adapter.verify_token(token)

            # Get user from database
            user = self.user_repository.get_by_id(payload["sub"])
            if not user or not user.is_active:
                g.user = None
                return

            g.user = {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "organization_id": user.organization_id,
                "role": user.role.value,
                "is_authenticated": True,
            }

        except Exception:
            g.user = None

    def register_auth_routes(self, app: Flask):
        """Register authentication routes."""

        @app.route("/auth/login", methods=["POST"])
        def login():
            """Login endpoint."""
            data = request.get_json()

            if not data or not data.get("email") or not data.get("password"):
                return jsonify({"error": "Email and password required"}), 400

            # Get user by email
            user = self.user_repository.get_by_email(data["email"])
            if not user or not user.is_active:
                return jsonify({"error": "Invalid credentials"}), 401

            # Verify password
            if not self.jwt_adapter.verify_password(
                data["password"],
                user.password_hash,
            ):
                return jsonify({"error": "Invalid credentials"}), 401

            # Create tokens
            access_token = self.jwt_adapter.create_access_token(
                user_id=user.id,
                organization_id=user.organization_id,
                role=user.role.value,
                email=user.email,
            )

            refresh_token = self.jwt_adapter.create_refresh_token(user.id)

            return jsonify(
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "name": user.name,
                        "organization_id": user.organization_id,
                        "role": user.role.value,
                    },
                }
            )

        @app.route("/auth/refresh", methods=["POST"])
        def refresh():
            """Refresh token endpoint."""
            data = request.get_json()

            if not data or not data.get("refresh_token"):
                return jsonify({"error": "Refresh token required"}), 400

            try:
                payload = self.jwt_adapter.verify_token(data["refresh_token"])

                if payload.get("type") != "refresh":
                    return jsonify({"error": "Invalid refresh token"}), 401

                # Get user
                user = self.user_repository.get_by_id(payload["sub"])
                if not user or not user.is_active:
                    return jsonify({"error": "User not found"}), 404

                # Create new access token
                access_token = self.jwt_adapter.create_access_token(
                    user_id=user.id,
                    organization_id=user.organization_id,
                    role=user.role.value,
                    email=user.email,
                )

                return jsonify({"access_token": access_token})

            except Exception as e:
                return jsonify({"error": str(e)}), 401

        @app.route("/auth/me", methods=["GET"])
        @self.require_auth
        def get_current_user():
            """Get current user info."""
            return jsonify(
                {
                    "user": {
                        "id": g.user["id"],
                        "email": g.user["email"],
                        "name": g.user["name"],
                        "organization_id": g.user["organization_id"],
                        "role": g.user["role"],
                    }
                }
            )

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
                            "message": "Please provide a valid access token",
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


def setup_jwt_auth(
    app: Flask,
    secret_key: str,
    user_repository: UserRepositoryPort,
) -> FlaskJWTMiddleware:
    """Setup JWT Auth for Flask app."""
    from .jwt_auth_adapter import JWTAuthAdapter, JWTConfig

    jwt_config = JWTConfig(secret_key=secret_key)
    jwt_adapter = JWTAuthAdapter(jwt_config)

    return FlaskJWTMiddleware(app, jwt_adapter, user_repository)
