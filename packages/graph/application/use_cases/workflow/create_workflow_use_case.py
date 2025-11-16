"""Create workflow use case implementation."""

from application.ports import (
    AuthorizationPort,
    WorkflowRepositoryPort,
    WorkflowValidationPort,
)
from application.use_cases.dto import CreateWorkflowRequestDTO, WorkflowDTO
from domain.entities import Workflow, WorkflowType
from domain.exceptions import AuthorizationError, ValidationError


class CreateWorkflowUseCase:
    """Use case for creating new workflows."""

    def __init__(
        self,
        workflow_repository: WorkflowRepositoryPort,
        workflow_validator: WorkflowValidationPort,
        authorization_service: AuthorizationPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            workflow_repository: Repository for workflow operations
            workflow_validator: Service for workflow validation
            authorization_service: Service for authorization checks
        """
        self.workflow_repository = workflow_repository
        self.workflow_validator = workflow_validator
        self.authorization_service = authorization_service

    def execute(self, request: CreateWorkflowRequestDTO) -> WorkflowDTO:
        """Execute the create workflow use case.

        Args:
            request: Create workflow request DTO

        Returns:
            Created workflow DTO

        Raises:
            ValidationError: If request validation fails
            AuthorizationError: If user is not authorized
        """
        # Validate input
        self._validate_request(request)

        # Check authorization
        self._check_authorization(request)

        # Validate workflow definition
        self._validate_workflow_definition(request)

        # Create workflow entity
        workflow = self._create_workflow_entity(request)

        # Save to repository
        created_workflow = self.workflow_repository.create(workflow)

        # Return DTO
        return self._create_workflow_dto(created_workflow)

    def _validate_request(self, request: CreateWorkflowRequestDTO) -> None:
        """Validate the create workflow request.

        Args:
            request: Request to validate

        Raises:
            ValidationError: If validation fails
        """
        if not request.name or not request.name.strip():
            raise ValidationError(
                message="Workflow name is required and cannot be empty", param="name"
            )

        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError(
                message="Tenant ID is required and cannot be empty", param="tenant_id"
            )

        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", param="user_id"
            )

        if not request.definition or not isinstance(request.definition, dict):
            raise ValidationError(
                message="Workflow definition is required and must be a dictionary",
                param="definition",
            )

        if not request.workflow_type or request.workflow_type not in [
            "ingestion",
            "query",
            "analytics",
            "export",
            "validation",
            "transformation",
        ]:
            raise ValidationError(
                message="Workflow type must be one of: ingestion, query, analytics, export, validation, transformation",
                param="workflow_type",
            )

        if not request.version or not request.version.strip():
            raise ValidationError(
                message="Version is required and cannot be empty", param="version"
            )

    def _check_authorization(self, request: CreateWorkflowRequestDTO) -> None:
        """Check if user is authorized to create workflows.

        Args:
            request: Request containing user and tenant information

        Raises:
            AuthorizationError: If user is not authorized
        """
        if not self.authorization_service.check_permission(
            user_id=request.user_id,
            resource_type="workflow",
            action="create",
            tenant_id=request.tenant_id,
        ):
            raise AuthorizationError(
                message="User is not authorized to create workflows",
                user_id=request.user_id,
                resource_type="workflow",
                action="create",
            )

    def _validate_workflow_definition(self, request: CreateWorkflowRequestDTO) -> None:
        """Validate the workflow definition.

        Args:
            request: Request containing workflow definition

        Raises:
            ValidationError: If workflow definition is invalid
        """
        is_valid, error_messages = self.workflow_validator.validate_workflow_definition(
            definition=request.definition, workflow_type=request.workflow_type
        )

        if not is_valid:
            raise ValidationError(
                message=f"Workflow definition validation failed: {'; '.join(error_messages)}",
                param="definition",
            )

    def _create_workflow_entity(self, request: CreateWorkflowRequestDTO) -> Workflow:
        """Create a workflow entity from the request.

        Args:
            request: Create workflow request

        Returns:
            Workflow entity
        """
        # Convert string workflow type to enum
        workflow_type_enum = WorkflowType(request.workflow_type.lower())

        return Workflow.create(
            name=request.name.strip(),
            tenant_id=request.tenant_id,
            definition=request.definition,
            workflow_type=workflow_type_enum,
            created_by=request.user_id,
            description=request.description.strip() if request.description else None,
            version=request.version.strip(),
        )

    def _create_workflow_dto(self, workflow: Workflow) -> WorkflowDTO:
        """Create a workflow DTO from the entity.

        Args:
            workflow: Workflow entity

        Returns:
            Workflow DTO
        """
        return WorkflowDTO(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            tenant_id=workflow.tenant_id,
            definition=workflow.definition,
            workflow_type=workflow.workflow_type.value.lower(),
            version=workflow.version,
            created_by=workflow.created_by,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            is_active=workflow.is_active,
        )
