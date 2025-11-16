"""Get job status use case implementation."""

import logging

from application.exceptions import ProgressUpdateError
from application.ports import (
    AuthorizationPort,
    JobRepositoryPort,
    WorkflowExecutionPort,
)
from application.use_cases.dto import GetJobStatusRequestDTO, JobDTO
from domain.exceptions import AuthorizationError, ValidationError


logger = logging.getLogger(__name__)


class GetJobStatusUseCase:
    """Use case for retrieving job status and progress information."""

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

    def execute(self, request: GetJobStatusRequestDTO) -> JobDTO:
        """Execute the get job status use case.

        Args:
            request: Get job status request DTO

        Returns:
            Job DTO with current status and progress

        Raises:
            ValidationError: If request validation fails
            AuthorizationError: If user is not authorized
            ProgressUpdateError: If job progress retrieval fails
        """
        # Validate input
        self._validate_request(request)

        # Get job from repository
        job = self._get_job(request)

        # Check authorization
        self._check_authorization(request, job)

        # Update job with latest progress if running
        updated_job = self._update_job_progress(job)

        # Return job DTO
        return self._create_job_dto(updated_job)

    def _validate_request(self, request: GetJobStatusRequestDTO) -> None:
        """Validate the get job status request.

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

    def _get_job(self, request: GetJobStatusRequestDTO):
        """Get the job from the repository.

        Args:
            request: Get job status request

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

    def _check_authorization(self, request: GetJobStatusRequestDTO, job) -> None:
        """Check if user is authorized to view job status.

        Args:
            request: Request containing user information
            job: Job entity

        Raises:
            AuthorizationError: If user is not authorized
        """
        # Check if user can view jobs in general
        if not self.authorization_service.check_permission(
            user_id=request.user_id,
            resource_type="job",
            action="read",
            tenant_id=request.tenant_id,
        ):
            raise AuthorizationError(
                message="User is not authorized to view job status",
                user_id=request.user_id,
                resource_type="job",
                action="read",
            )

        # Additional check: user can only view their own jobs unless they have admin permissions
        if (
            job.created_by != request.user_id
            and not self.authorization_service.check_permission(
                user_id=request.user_id,
                resource_type="job",
                action="read_all",
                tenant_id=request.tenant_id,
            )
        ):
            raise AuthorizationError(
                message="User is not authorized to view this job",
                user_id=request.user_id,
                resource_type="job",
                action="read",
            )

    def _update_job_progress(self, job):
        """Update job with latest progress information if it's running.

        Args:
            job: Job entity

        Returns:
            Updated job entity

        Raises:
            ProgressUpdateError: If retrieving progress information fails
        """
        # Only update progress for running jobs
        if job.status.value.lower() == "running":
            try:
                # Get latest progress from execution service
                progress_info = self.workflow_execution_service.get_job_progress(
                    job_id=job.id, tenant_id=job.tenant_id
                )

                if progress_info:
                    # Update job progress
                    if "progress_percentage" in progress_info:
                        job.update_progress(
                            percentage=progress_info["progress_percentage"],
                            message=progress_info.get("message"),
                        )

                    # Update job status if it has changed
                    if (
                        "status" in progress_info
                        and progress_info["status"] != job.status.value.lower()
                    ):
                        if progress_info["status"] == "completed":
                            job.complete(progress_info.get("output_data"))
                        elif progress_info["status"] == "failed":
                            job.fail(progress_info.get("error_message", "Job failed"))
                        elif progress_info["status"] == "cancelled":
                            job.cancel()

                    # Save updated job
                    job = self.job_repository.update(job)

            except Exception as exc:
                logger.exception(
                    "Failed to update job progress",
                    extra={"job_id": job.id, "tenant_id": job.tenant_id},
                )
                raise ProgressUpdateError(
                    job_id=job.id, tenant_id=job.tenant_id, cause=exc
                ) from exc

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
