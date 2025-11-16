"""Retry failed job use case implementation."""

from application.ports import (
    AuthorizationPort,
    JobRepositoryPort,
    WorkflowExecutionPort,
    WorkflowRepositoryPort,
)
from application.use_cases.dto import JobDTO, RetryFailedJobRequestDTO
from domain.exceptions import AuthorizationError, ValidationError


class RetryFailedJobUseCase:
    """Use case for retrying failed jobs."""

    def __init__(
        self,
        job_repository: JobRepositoryPort,
        workflow_repository: WorkflowRepositoryPort,
        workflow_execution_service: WorkflowExecutionPort,
        authorization_service: AuthorizationPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            job_repository: Repository for job operations
            workflow_repository: Repository for workflow operations
            workflow_execution_service: Service for workflow execution
            authorization_service: Service for authorization checks
        """
        self.job_repository = job_repository
        self.workflow_repository = workflow_repository
        self.workflow_execution_service = workflow_execution_service
        self.authorization_service = authorization_service

    def execute(self, request: RetryFailedJobRequestDTO) -> JobDTO:
        """Execute the retry failed job use case.

        Args:
            request: Retry failed job request DTO

        Returns:
            Updated job DTO with retry status

        Raises:
            ValidationError: If request validation fails or job cannot be retried
            AuthorizationError: If user is not authorized
        """
        # Validate input
        self._validate_request(request)

        # Get job from repository
        job = self._get_job(request)

        # Check authorization
        self._check_authorization(request, job)

        # Validate job can be retried
        self._validate_job_can_be_retried(job, request.reset_retry_count)

        # Get workflow for retry
        workflow = self._get_workflow(job)

        # Retry the job
        retried_job = self._retry_job(job, workflow, request.reset_retry_count)

        # Return job DTO
        return self._create_job_dto(retried_job)

    def _validate_request(self, request: RetryFailedJobRequestDTO) -> None:
        """Validate the retry failed job request.

        Args:
            request: Request to validate

        Raises:
            ValidationError: If validation fails
        """
        if not request.job_id or not request.job_id.strip():
            raise ValidationError(
                message="Job ID is required and cannot be empty", param="job_id"
            )

        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError(
                message="Tenant ID is required and cannot be empty", param="tenant_id"
            )

        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", param="user_id"
            )

        if not isinstance(request.reset_retry_count, bool):
            raise ValidationError(
                message="Reset retry count must be a boolean value",
                param="reset_retry_count",
            )

    def _get_job(self, request: RetryFailedJobRequestDTO):
        """Get the job from the repository.

        Args:
            request: Retry failed job request

        Returns:
            Job entity

        Raises:
            ValidationError: If job is not found
        """
        job = self.job_repository.get_by_id(
            job_id=request.job_id, tenant_id=request.tenant_id
        )

        if not job:
            raise ValidationError(
                message=f"Job with ID {request.job_id} not found", param="job_id"
            )

        return job

    def _check_authorization(self, request: RetryFailedJobRequestDTO, job) -> None:
        """Check if user is authorized to retry the job.

        Args:
            request: Request containing user information
            job: Job entity

        Raises:
            AuthorizationError: If user is not authorized
        """
        # Check if user can retry jobs in general
        if not self.authorization_service.check_permission(
            user_id=request.user_id,
            resource_type="job",
            action="retry",
            tenant_id=request.tenant_id,
        ):
            raise AuthorizationError(
                message="User is not authorized to retry jobs",
                user_id=request.user_id,
                resource_type="job",
                action="retry",
            )

        # Additional check: user can only retry their own jobs unless they have admin permissions
        if (
            job.created_by != request.user_id
            and not self.authorization_service.check_permission(
                user_id=request.user_id,
                resource_type="job",
                action="retry_all",
                tenant_id=request.tenant_id,
            )
        ):
            raise AuthorizationError(
                message="User is not authorized to retry this job",
                user_id=request.user_id,
                resource_type="job",
                action="retry",
            )

    def _validate_job_can_be_retried(self, job, reset_retry_count: bool) -> None:
        """Validate that the job can be retried.

        Args:
            job: Job entity
            reset_retry_count: Whether to reset the retry count

        Raises:
            ValidationError: If job cannot be retried
        """
        # Job must be in failed status to be retried
        if job.status.value.lower() != "failed":
            raise ValidationError(
                message=f"Job with ID {job.id} is not in failed status and cannot be retried (current status: {job.status.value.lower()})",
                param="job_id",
            )

        # Check if job can be retried (unless we're resetting the retry count)
        if not reset_retry_count and not job.can_retry():
            raise ValidationError(
                message=f"Job with ID {job.id} has exceeded maximum retry attempts ({job.retry_count}/{job.max_retries})",
                param="job_id",
            )

    def _get_workflow(self, job):
        """Get the workflow associated with the job.

        Args:
            job: Job entity

        Returns:
            Workflow entity

        Raises:
            ValidationError: If workflow is not found or inactive
        """
        workflow = self.workflow_repository.get_by_id(
            workflow_id=job.workflow_id, tenant_id=job.tenant_id
        )

        if not workflow:
            raise ValidationError(
                message=f"Workflow with ID {job.workflow_id} not found",
                param="workflow_id",
            )

        if not workflow.is_active:
            raise ValidationError(
                message=f"Workflow with ID {job.workflow_id} is not active and cannot be retried",
                param="workflow_id",
            )

        return workflow

    def _retry_job(self, job, workflow, reset_retry_count: bool):
        """Retry the failed job.

        Args:
            job: Job entity to retry
            workflow: Workflow entity
            reset_retry_count: Whether to reset the retry count

        Returns:
            Updated job entity
        """
        # Reset retry count if requested
        if reset_retry_count:
            job.retry_count = 0

        # Attempt to retry the job
        if not job.retry():
            # This shouldn't happen if validation passed, but just in case
            raise ValidationError(
                message=f"Job with ID {job.id} cannot be retried", param="job_id"
            )

        # Save the updated job
        job = self.job_repository.update(job)

        try:
            # Start the job execution again
            job.start()
            self.job_repository.update(job)

            # Execute the workflow again
            self.workflow_execution_service.execute_workflow(
                workflow=workflow, input_parameters=job.input_parameters, job_id=job.id
            )

        except Exception as e:
            # If execution fails, mark job as failed again
            job.fail(f"Retry failed: {str(e)}")
            job = self.job_repository.update(job)

        return job

    def _create_job_dto(self, job) -> JobDTO:
        """Create a job DTO from the entity.

        Args:
            job: Job entity

        Returns:
            Job DTO
        """
        return JobDTO(
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
