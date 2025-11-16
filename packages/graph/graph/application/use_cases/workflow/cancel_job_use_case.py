"""Cancel job use case implementation."""

import logging

from application.ports import (
    AuthorizationPort,
    JobRepositoryPort,
    WorkflowExecutionPort,
)
from application.use_cases.dto import CancelJobRequestDTO, JobDTO
from domain.exceptions import AuthorizationError, ValidationError


logger = logging.getLogger(__name__)


class CancelJobUseCase:
    """Use case for cancelling running jobs."""

    def __init__(
        self,
        job_repository: JobRepositoryPort,
        workflow_execution_service: WorkflowExecutionPort,
        authorization_service: AuthorizationPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            job_repository: Repository for job operations
            workflow_execution_service: Service for workflow execution
            authorization_service: Service for authorization checks
        """
        self.job_repository = job_repository
        self.workflow_execution_service = workflow_execution_service
        self.authorization_service = authorization_service

    def execute(self, request: CancelJobRequestDTO) -> JobDTO:
        """Execute the cancel job use case.

        Args:
            request: Cancel job request DTO

        Returns:
            Updated job DTO with cancelled status

        Raises:
            ValidationError: If request validation fails or job cannot be cancelled
            AuthorizationError: If user is not authorized
        """
        # Validate input
        self._validate_request(request)

        # Get job from repository
        job = self._get_job(request)

        # Check authorization
        self._check_authorization(request, job)

        # Validate job can be cancelled
        self._validate_job_can_be_cancelled(job)

        # Cancel the job
        cancelled_job = self._cancel_job(job, request.reason)

        # Return job DTO
        return self._create_job_dto(cancelled_job)

    def _validate_request(self, request: CancelJobRequestDTO) -> None:
        """Validate the cancel job request.

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

    def _get_job(self, request: CancelJobRequestDTO):
        """Get the job from the repository.

        Args:
            request: Cancel job request

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

    def _check_authorization(self, request: CancelJobRequestDTO, job) -> None:
        """Check if user is authorized to cancel the job.

        Args:
            request: Request containing user information
            job: Job entity

        Raises:
            AuthorizationError: If user is not authorized
        """
        # Check if user can cancel jobs in general
        if not self.authorization_service.check_permission(
            user_id=request.user_id,
            resource_type="job",
            action="cancel",
            tenant_id=request.tenant_id,
        ):
            raise AuthorizationError(
                message="User is not authorized to cancel jobs",
                user_id=request.user_id,
                resource_type="job",
                action="cancel",
            )

        # Additional check: user can only cancel their own jobs unless they have admin permissions
        if (
            job.created_by != request.user_id
            and not self.authorization_service.check_permission(
                user_id=request.user_id,
                resource_type="job",
                action="cancel_all",
                tenant_id=request.tenant_id,
            )
        ):
            raise AuthorizationError(
                message="User is not authorized to cancel this job",
                user_id=request.user_id,
                resource_type="job",
                action="cancel",
            )

    def _validate_job_can_be_cancelled(self, job) -> None:
        """Validate that the job can be cancelled.

        Args:
            job: Job entity

        Raises:
            ValidationError: If job cannot be cancelled
        """
        if job.is_terminal():
            raise ValidationError(
                message=f"Job with ID {job.id} is already in terminal state ({job.status.value.lower()}) and cannot be cancelled",
                param="job_id",
            )

    def _cancel_job(self, job, reason: str = None):
        """Cancel the job.

        Args:
            job: Job entity to cancel
            reason: Optional cancellation reason

        Returns:
            Updated job entity
        """
        try:
            # Try to cancel the job in the execution service first
            cancelled = self.workflow_execution_service.cancel_job(
                job_id=job.id, tenant_id=job.tenant_id
            )

            if not cancelled:
                # If execution service couldn't cancel it, re-check current status
                refreshed_job = self.job_repository.get_by_id(
                    job_id=job.id, tenant_id=job.tenant_id
                )
                if refreshed_job and refreshed_job.is_terminal():
                    return refreshed_job
                raise ValidationError(
                    message=f"Job with ID {job.id} could not be cancelled",
                    param="job_id",
                )

        except Exception as e:
            logger.exception("Failed to cancel job %s", job.id)
            raise

        # Update job status to cancelled
        job.cancel()

        # Add cancellation reason to output data if provided
        if reason:
            if job.output_data is None:
                job.output_data = {}
            job.output_data["cancellation_reason"] = reason

        # Save updated job
        return self.job_repository.update(job)

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
