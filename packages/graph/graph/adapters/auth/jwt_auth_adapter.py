"""JWT-based authentication adapter for production use."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import bcrypt
import jwt

from application.exceptions import AuthorizationError


@dataclass
class JWTConfig:
    """JWT configuration."""

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7


class JWTAuthAdapter:
    """JWT-based authentication adapter."""

    def __init__(self, config: JWTConfig):
        """Initialize JWT auth adapter."""
        self.config = config
        self.secret_key = config.secret_key
        self.algorithm = config.algorithm

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

    def create_access_token(
        self,
        user_id: str,
        organization_id: str,
        role: str,
        email: str,
    ) -> str:
        """Create JWT access token."""
        expire = datetime.utcnow() + timedelta(
            minutes=self.config.access_token_expire_minutes
        )

        payload = {
            "sub": user_id,
            "email": email,
            "organization_id": organization_id,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token."""
        expire = datetime.utcnow() + timedelta(
            days=self.config.refresh_token_expire_days
        )

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthorizationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthorizationError("Invalid token")

    def refresh_access_token(
        self, refresh_token: str, user_data: Dict[str, Any]
    ) -> str:
        """Create new access token from refresh token."""
        payload = self.verify_token(refresh_token)

        if payload.get("type") != "refresh":
            raise AuthorizationError("Invalid refresh token")

        return self.create_access_token(
            user_id=user_data["id"],
            organization_id=user_data["organization_id"],
            role=user_data["role"],
            email=user_data["email"],
        )
