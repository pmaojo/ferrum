"""Use case for updating graph access policies."""

from dataclasses import dataclass
from typing import List, Optional

from application.exceptions import (
    ApplicationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from application.ports import AuthorizationServicePort, TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, TenantScopedRequestDTO
from domain.entities import GraphAccessPolicy, UserRole

from .create_graph_access_policy_use_case import (
    GraphAccessPolicyDTO,
    GraphAccessPolicyRepositoryPort,
)


@dataclass
class UpdateGraphAccessPolicyRequest(TenantScopedRequestDTO):
    kg_id: str
    target_user_id: str
    role: Optional[str] = None
    permissions: Optional[List[str]] = None


@dataclass
class UpdateGraphAccessPolicyResponse(BaseResponseDTO):
    policy: Optional[GraphAccessPolicyDTO] = None


class UpdateGraphAccessPolicyUseCase(
    BaseUseCase[UpdateGraphAccessPolicyRequest, UpdateGraphAccessPolicyResponse]
):
    """Update existing policies."""

    def __init__(
        self,
        repository: GraphAccessPolicyRepositoryPort,
        authorization_service: AuthorizationServicePort,
        tracer: TracingPort,
    ) -> None:
        super().__init__()
        self.repository = repository
        self.authorization_service = authorization_service
        self.tracer = tracer

    def _validate_request_internal(
        self, request: UpdateGraphAccessPolicyRequest
    ) -> None:
        if not request.kg_id or not request.kg_id.strip():
            raise ValidationError(
                message="Knowledge graph ID is required", field="kg_id"
            )
        if not request.target_user_id or not request.target_user_id.strip():
            raise ValidationError(
                message="Target user ID is required", field="target_user_id"
            )
        if request.role is None and request.permissions is None:
            raise ValidationError(message="Nothing to update", field="update")
        if request.role is not None and request.role not in [r.value for r in UserRole]:
            raise ValidationError(message="Invalid role", field="role")
        if request.permissions is not None and (
            not isinstance(request.permissions, list)
            or not all(isinstance(p, str) for p in request.permissions)
        ):
            raise ValidationError(
                message="Permissions must be list of strings", field="permissions"
            )

    async def _execute_internal(
        self, request: UpdateGraphAccessPolicyRequest
    ) -> UpdateGraphAccessPolicyResponse:
        with self.tracer.start_span(
            name="update_graph_access_policy",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        ):
            try:
                self.authorization_service.check_permission(
                    user_id=request.user_id,
                    resource_id=request.kg_id,
                    action="manage_access",
                )
                existing = self.repository.get(
                    request.kg_id, request.tenant_id, request.target_user_id
                )
                if existing is None:
                    raise NotFoundError(
                        message="Policy not found",
                        resource_type="graph_access_policy",
                        resource_id=request.target_user_id,
                    )
                new_role = (
                    UserRole(request.role)
                    if request.role is not None
                    else existing.role
                )
                new_permissions = (
                    request.permissions
                    if request.permissions is not None
                    else existing.permissions
                )
                updated = self.repository.update(
                    GraphAccessPolicy(
                        kg_id=existing.kg_id,
                        tenant_id=existing.tenant_id,
                        user_id=existing.user_id,
                        role=new_role,
                        permissions=new_permissions,
                    )
                )
                dto = GraphAccessPolicyDTO(
                    kg_id=updated.kg_id,
                    tenant_id=updated.tenant_id,
                    user_id=updated.user_id,
                    role=updated.role.value,
                    permissions=updated.permissions,
                )
                return UpdateGraphAccessPolicyResponse(
                    success=True, processing_time_ms=0.0, policy=dto
                )
            except (ValidationError, AuthorizationError, NotFoundError) as e:
                return UpdateGraphAccessPolicyResponse(
                    success=False, processing_time_ms=0.0, error_message=str(e)
                )
            except Exception as e:  # pragma: no cover
                raise ApplicationError(
                    message=str(e), error_code="UPDATE_POLICY_FAILED"
                ) from e
