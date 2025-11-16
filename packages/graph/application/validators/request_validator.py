from __future__ import annotations

from dataclasses import dataclass

from application.exceptions import ValidationError


def _is_blank(value: str | None) -> bool:
    return value is None or value.strip() == ""


@dataclass
class RequestValidator:
    """Utility class for common request validations."""

    def validate_tenant_id(self, tenant_id: str | None) -> None:
        if _is_blank(tenant_id):
            raise ValidationError(message="Tenant ID is required", field="tenant_id")

    def validate_user_id(self, user_id: str | None) -> None:
        if _is_blank(user_id):
            raise ValidationError(message="User ID is required", field="user_id")

    def validate_kg_id(self, kg_id: str | None) -> None:
        if _is_blank(kg_id):
            raise ValidationError(
                message="Knowledge graph ID is required", field="kg_id"
            )

    def validate_ids(
        self, tenant_id: str | None, user_id: str | None, kg_id: str | None
    ) -> None:
        self.validate_tenant_id(tenant_id)
        self.validate_user_id(user_id)
        self.validate_kg_id(kg_id)
