"""Use case for deleting graph access policies."""

from dataclasses import dataclass

from application.exceptions import ApplicationError, AuthorizationError, ValidationError
from application.ports import AuthorizationServicePort, TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, TenantScopedRequestDTO

from .create_graph_access_policy_use_case import GraphAccessPolicyRepositoryPort


@dataclass
class DeleteGraphAccessPolicyRequest(TenantScopedRequestDTO):
    kg_id: str
    target_user_id: str


@dataclass
class DeleteGraphAccessPolicyResponse(BaseResponseDTO):
    deleted: bool = False


class DeleteGraphAccessPolicyUseCase(
    BaseUseCase[DeleteGraphAccessPolicyRequest, DeleteGraphAccessPolicyResponse]
):
    """Delete policies after authorization."""

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
        self, request: DeleteGraphAccessPolicyRequest
    ) -> None:
        if not request.kg_id or not request.kg_id.strip():
            raise ValidationError(
                message="Knowledge graph ID is required", field="kg_id"
            )
        if not request.target_user_id or not request.target_user_id.strip():
            raise ValidationError(
                message="Target user ID is required", field="target_user_id"
            )

    async def _execute_internal(
        self, request: DeleteGraphAccessPolicyRequest
    ) -> DeleteGraphAccessPolicyResponse:
        with self.tracer.start_span(
            name="delete_graph_access_policy",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        ):
            try:
                self.authorization_service.check_permission(
                    user_id=request.user_id,
                    resource_id=request.kg_id,
                    action="manage_access",
                )
                success = self.repository.delete(
                    request.kg_id, request.tenant_id, request.target_user_id
                )
                return DeleteGraphAccessPolicyResponse(
                    success=True, processing_time_ms=0.0, deleted=success
                )
            except (ValidationError, AuthorizationError) as e:
                return DeleteGraphAccessPolicyResponse(
                    success=False, processing_time_ms=0.0, error_message=str(e)
                )
            except Exception as e:  # pragma: no cover
                raise ApplicationError(
                    message=str(e), error_code="DELETE_POLICY_FAILED"
                ) from e
