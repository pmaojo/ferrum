"""Use case for listing graph access policies."""

from dataclasses import dataclass, field
from typing import List

from application.exceptions import ApplicationError, AuthorizationError, ValidationError
from application.ports import AuthorizationServicePort, TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, TenantScopedRequestDTO

from .create_graph_access_policy_use_case import (
    GraphAccessPolicyDTO,
    GraphAccessPolicyRepositoryPort,
)


@dataclass
class ListGraphAccessPoliciesRequest(TenantScopedRequestDTO):
    kg_id: str


@dataclass
class ListGraphAccessPoliciesResponse(BaseResponseDTO):
    policies: List[GraphAccessPolicyDTO] = field(default_factory=list)


class ListGraphAccessPoliciesUseCase(
    BaseUseCase[ListGraphAccessPoliciesRequest, ListGraphAccessPoliciesResponse]
):
    """List all policies for a knowledge graph."""

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
        self, request: ListGraphAccessPoliciesRequest
    ) -> None:
        if not request.kg_id or not request.kg_id.strip():
            raise ValidationError(
                message="Knowledge graph ID is required", field="kg_id"
            )

    async def _execute_internal(
        self, request: ListGraphAccessPoliciesRequest
    ) -> ListGraphAccessPoliciesResponse:
        with self.tracer.start_span(
            name="list_graph_access_policies",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        ):
            try:
                self.authorization_service.check_permission(
                    user_id=request.user_id,
                    resource_id=request.kg_id,
                    action="manage_access",
                )
                items = self.repository.list_for_kg(request.kg_id, request.tenant_id)
                dtos = [
                    GraphAccessPolicyDTO(
                        kg_id=p.kg_id,
                        tenant_id=p.tenant_id,
                        user_id=p.user_id,
                        role=p.role.value,
                        permissions=p.permissions,
                    )
                    for p in items
                ]
                return ListGraphAccessPoliciesResponse(
                    success=True, processing_time_ms=0.0, policies=dtos
                )
            except (ValidationError, AuthorizationError) as e:
                return ListGraphAccessPoliciesResponse(
                    success=False,
                    processing_time_ms=0.0,
                    error_message=str(e),
                    policies=[],
                )
            except Exception as e:  # pragma: no cover
                raise ApplicationError(
                    message=str(e), error_code="LIST_POLICY_FAILED"
                ) from e
