from enum import Enum
from typing import Set
from pydantic import BaseModel


class Role(str, Enum):
    """Available user roles."""
    QUERY = "query"
    INGEST = "ingest"
    ADMIN = "admin"


# Mapping of roles to permissions
default_permissions = {
    Role.ADMIN: {"query", "ingest"},
    Role.QUERY: {"query"},
    Role.INGEST: {"ingest"},
}


class User(BaseModel):
    """Authenticated user model."""
    username: str
    role: Role

    def permissions(self) -> Set[str]:
        return default_permissions.get(self.role, set())

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions()
