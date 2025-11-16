"""Execute workflow use case implementation."""

from typing import Any, Dict

from application.ports import (
    AuthorizationPort,
    JobRepositoryPort,
    WorkflowExecutionPort,
    WorkflowRepositoryPort,
)
from application.use_cases.dto import (
    ExecuteWorkflowRequestDTO,
    JobDTO,
    WorkflowDTO,
    WorkflowExecutionResponseDTO,
)
from domain.entities import Job
from domain.exceptions import AuthorizationError, ValidationError


class ExecuteWorkflowUseCase:
    """Use case for executing workflows asynchronously."""

    def __init__(
        self,
        workflow_repository: WorkflowRepositoryPort,
        job_repository: JobRepositoryPort,
        workflow_execution_service: WorkflowExecutionPort,
        authorization_service: AuthorizationPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            workflow_repository: Repository for workflow operations
            job_repository: Repository for job operations
            workflow_execution_service: Service for workflow execution
            authorization_service: Service for authorization checks
        """
        self.workflow_repository = workflow_repository
        self.job_repository = job_repository
        self.workflow_execution_service = workflow_execution_service
        self.authorization_service = authorization_service

    def execute(
        self, request: ExecuteWorkflowRequestDTO
    ) -> WorkflowExecutionResponseDTO:
        """Execute the workflow execution use case.

        Args:
            request: Execute workflow request DTO

        Returns:
            Workflow execution response DTO

        Raises:
            ValidationError: If request validation fails
            AuthorizationError: If user is not authorized
        """
        # Validate input
        self._validate_request(request)

        # Check authorization
        self._check_authorization(request)

        # Get workflow
        workflow = self._get_workflow(request)

        # Create job for tracking
        job = self._create_job(request, workflow.id)

        # Start asynchronous execution
        execution_started = self._start_execution(
            workflow, job, request.input_parameters
        )

        # Return response
        return self._create_response(workflow, job, execution_started)

    def _validate_request(self, request: ExecuteWorkflowRequestDTO) -> None:
        """Validate the execute workflow request.

        Args:
            request: Request to validate

        Raises:
            ValidationError: If validation fails
        """
        if not request.workflow_id or not request.workflow_id.strip():
            raise ValidationError(
                message="Workflow ID is required and cannot be empty",
                param="workflow_id",
            )

        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError(
                message="Tenant ID is required and cannot be empty", param="tenant_id"
            )

        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", param="user_id"
            )

        if not isinstance(request.input_parameters, dict):
            raise ValidationError(
                message="Input parameters must be a dictionary",
                param="input_parameters",
            )

        if not isinstance(request.max_retries, int) or request.max_retries < 0:
            raise ValidationError(
                message="Max retries must be a non-negative integer",
                param="max_retries",
            )

    def _check_authorization(self, request: ExecuteWorkflowRequestDTO) -> None:
        """Check if user is authorized to execute workflows.

        Args:
            request: Request containing user and tenant information

        Raises:
            AuthorizationError: If user is not authorized
        """
        if not self.authorization_service.check_permission(
            user_id=request.user_id,
            resource_type="workflow",
            action="execute",
            tenant_id=request.tenant_id,
        ):
            raise AuthorizationError(
                message="User is not authorized to execute workflows",
                user_id=request.user_id,
                resource_type="workflow",
                action="execute",
            )

    def _get_workflow(self, request: ExecuteWorkflowRequestDTO):
        """Get the workflow to execute.

        Args:
            request: Execute workflow request

        Returns:
            Workflow entity

        Raises:
            ValidationError: If workflow is not found or inactive
        """
        workflow = self.workflow_repository.get_by_id(
            workflow_id=request.workflow_id, tenant_id=request.tenant_id
        )

        if not workflow:
            raise ValidationError(
                message=f"Workflow with ID {request.workflow_id} not found",
                param="workflow_id",
            )

        if not workflow.is_active:
            raise ValidationError(
                message=f"Workflow with ID {request.workflow_id} is not active",
                param="workflow_id",
            )

        return workflow

    def _create_job(self, request: ExecuteWorkflowRequestDTO, workflow_id: str) -> Job:
        """Create a job for tracking workflow execution.

        Args:
            request: Execute workflow request
            workflow_id: Workflow identifier

        Returns:
            Created job entity
        """
        job = Job.create(
            workflow_id=workflow_id,
            tenant_id=request.tenant_id,
            input_parameters=request.input_parameters,
            created_by=request.user_id,
            max_retries=request.max_retries,
        )

        return self.job_repository.create(job)

    def _start_execution(
        self, workflow, job: Job, input_parameters: Dict[str, Any]
    ) -> bool:
        """Start asynchronous workflow execution.

        Args:
            workflow: Workflow entity to execute
            job: Job entity for tracking
            input_parameters: Input parameters for execution

        Returns:
            True if execution started successfully, False otherwise
        """
        try:
            # Mark job as started
            job.start()
            self.job_repository.update(job)

            # Start asynchronous execution
            self.workflow_execution_service.execute_workflow(
                workflow=workflow, input_parameters=input_parameters, job_id=job.id
            )

            return True

        except Exception as e:
            # Mark job as failed
            job.fail(str(e))
            self.job_repository.update(job)
            return False

    def _create_response(
        self, workflow, job: Job, execution_started: bool
    ) -> WorkflowExecutionResponseDTO:
        """Create the workflow execution response.

        Args:
            workflow: Workflow entity
            job: Job entity
            execution_started: Whether execution started successfully

        Returns:
            Workflow execution response DTO
        """
        workflow_dto = WorkflowDTO(
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

        job_dto = JobDTO(
            id=job.id,
            workflow_id=job.workflow_id,
            tenant_id=job.tenant_id,
            status=job.status.value.lower(),
            input_parameters=job.input_parameters,
            output_data=job.output_data,
            error_message=job.error_message,
            progress_percentage=job.progress_percentage,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_by=job.created_by,
            created_at=job.created_at,
            updated_at=job.updated_at,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
        )

        message = (
            "Workflow execution started successfully"
            if execution_started
            else "Failed to start workflow execution"
        )

        return WorkflowExecutionResponseDTO(
            job=job_dto,
            workflow=workflow_dto,
            execution_started=execution_started,
            message=message,
        )
