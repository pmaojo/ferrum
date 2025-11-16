from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from application.ports import (
    UserRepositoryPort,
    OrganizationRepositoryPort,
    PasswordServicePort,
    AuthorizationServicePort,
    AuditServicePort,
)
from adapters.inmemory_tracing_adapter import InMemoryTracingAdapter
from application.use_cases.user_org.create_user_use_case import CreateUserUseCase
from domain.entities import User, Organization, UserRole, SubscriptionTier


class InMemoryUserRepository(UserRepositoryPort):
    """Simple in-memory user repository for demo purposes."""

    def __init__(self) -> None:
        self._users: Dict[str, User] = {}

    def create(self, user: User) -> User:
        self._users[user.id] = user
        return user

    def update(self, user: User) -> User:
        self._users[user.id] = user
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        return next((u for u in self._users.values() if u.email == email), None)

    def list_by_organization(
        self, organization_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[User], int]:
        users = [u for u in self._users.values() if u.organization_id == organization_id]
        return users, len(users)

    def delete_by_id(self, user_id: str) -> bool:
        return self._users.pop(user_id, None) is not None


class InMemoryOrganizationRepository(OrganizationRepositoryPort):
    """Minimal in-memory organization repository."""

    def __init__(self) -> None:
        self._orgs: Dict[str, Organization] = {}

    def create(self, organization: Organization) -> Organization:
        self._orgs[organization.id] = organization
        return organization

    def update(self, organization: Organization) -> Organization:
        self._orgs[organization.id] = organization
        return organization

    def get_by_id(self, organization_id: str) -> Optional[Organization]:
        return self._orgs.get(organization_id)

    def get_by_name(self, name: str) -> Optional[Organization]:
        return next((o for o in self._orgs.values() if o.name == name), None)

    def list_by_user(
        self, user_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Organization], int]:
        return list(self._orgs.values()), len(self._orgs)

    def delete_by_id(self, organization_id: str) -> bool:
        return self._orgs.pop(organization_id, None) is not None


class SimplePasswordService(PasswordServicePort):
    """Very basic password hashing using SHA256."""

    def hash_password(self, password: str) -> str:
        import hashlib

        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def verify_password(self, password: str, password_hash: str) -> bool:
        return self.hash_password(password) == password_hash


class SimpleAuthorizationService(AuthorizationServicePort):
    """Permit all operations; for demonstration only."""

    def check_permission(self, user_id: str, resource_id: str, action: str) -> None:
        return None

    def get_user_permissions(self, user_id: str, resource_id: Optional[str] = None) -> List[str]:
        return ["*"]

    def get_graph_access_policy(
        self, *, kg_id: str, tenant_id: str, user_id: str
    ) -> Optional[None]:
        return None


class SimpleAuditService(AuditServicePort):
    """No-op audit logger."""

    def log_activity(
        self,
        user_id: str,
        activity_type: str,
        description: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        metadata: Optional[Dict[str, any]] = None,
    ) -> None:
        return None

    def get_user_activity(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        activity_types: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, any]], int]:
        return [], 0


@lru_cache()
def get_create_user_use_case() -> CreateUserUseCase:
    tracer = InMemoryTracingAdapter()
    user_repo = InMemoryUserRepository()
    org_repo = InMemoryOrganizationRepository()
    password_service = SimplePasswordService()
    auth_service = SimpleAuthorizationService()
    audit_service = SimpleAuditService()
    return CreateUserUseCase(
        user_repository=user_repo,
        organization_repository=org_repo,
        password_service=password_service,
        authorization_service=auth_service,
        audit_service=audit_service,
        tracer=tracer,
    )

