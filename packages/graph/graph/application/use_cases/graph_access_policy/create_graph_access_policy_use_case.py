"""Use case for creating graph access policies."""

from dataclasses import dataclass
from typing import List, Optional, Protocol

from application.exceptions import ApplicationError, AuthorizationError, ValidationError
from application.ports import AuthorizationServicePort, TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, TenantScopedRequestDTO
from domain.entities import GraphAccessPolicy, UserRole


class GraphAccessPolicyRepositoryPort(Protocol):
    """Persistence operations for access policies."""

    def create(self, policy: GraphAccessPolicy) -> GraphAccessPolicy: ...

    def update(self, policy: GraphAccessPolicy) -> GraphAccessPolicy: ...

    def delete(self, kg_id: str, tenant_id: str, user_id: str) -> bool: ...

    def get(
        self, kg_id: str, tenant_id: str, user_id: str
    ) -> Optional[GraphAccessPolicy]: ...

    def list_for_kg(self, kg_id: str, tenant_id: str) -> List[GraphAccessPolicy]: ...


@dataclass
class GraphAccessPolicyDTO:
    kg_id: str
    tenant_id: str
    user_id: str
    role: str
    permissions: List[str]


@dataclass
class CreateGraphAccessPolicyRequest(TenantScopedRequestDTO):
    kg_id: str
    target_user_id: str
    role: str
    permissions: List[str]


@dataclass
class CreateGraphAccessPolicyResponse(BaseResponseDTO):
    policy: Optional[GraphAccessPolicyDTO] = None


class CreateGraphAccessPolicyUseCase(
    BaseUseCase[CreateGraphAccessPolicyRequest, CreateGraphAccessPolicyResponse]
):
    """Create new policies after authorization checks."""

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
        self, request: CreateGraphAccessPolicyRequest
    ) -> None:
        if not request.kg_id or not request.kg_id.strip():
            raise ValidationError(
                message="Knowledge graph ID is required", field="kg_id"
            )
        if not request.target_user_id or not request.target_user_id.strip():
            raise ValidationError(
                message="Target user ID is required", field="target_user_id"
            )
        if request.role not in [r.value for r in UserRole]:
            raise ValidationError(message="Invalid role", field="role")
        if not isinstance(request.permissions, list) or not all(
            isinstance(p, str) for p in request.permissions
        ):
            raise ValidationError(
                message="Permissions must be list of strings", field="permissions"
            )

    async def _execute_internal(
        self, request: CreateGraphAccessPolicyRequest
    ) -> CreateGraphAccessPolicyResponse:
        with self.tracer.start_span(
            name="create_graph_access_policy",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        ):
            try:
                self.authorization_service.check_permission(
                    user_id=request.user_id,
                    resource_id=request.kg_id,
                    action="manage_access",
                )
                existing = self.authorization_service.get_graph_access_policy(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    user_id=request.target_user_id,
                )
                if existing:
                    raise ValidationError(
                        message="Policy already exists for user",
                        field="target_user_id",
                    )
                policy = GraphAccessPolicy(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    user_id=request.target_user_id,
                    role=UserRole(request.role),
                    permissions=request.permissions,
                )
                created = self.repository.create(policy)
                dto = GraphAccessPolicyDTO(
                    kg_id=created.kg_id,
                    tenant_id=created.tenant_id,
                    user_id=created.user_id,
                    role=created.role.value,
                    permissions=created.permissions,
                )
                return CreateGraphAccessPolicyResponse(
                    success=True, processing_time_ms=0.0, policy=dto
                )
            except (ValidationError, AuthorizationError) as e:
                return CreateGraphAccessPolicyResponse(
                    success=False, processing_time_ms=0.0, error_message=str(e)
                )
            except Exception as e:  # pragma: no cover - unexpected error path
                raise ApplicationError(
                    message=str(e), error_code="CREATE_POLICY_FAILED"
                ) from e
