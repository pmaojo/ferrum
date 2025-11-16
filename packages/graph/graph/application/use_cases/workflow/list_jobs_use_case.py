"""List jobs use case implementation."""

from datetime import datetime
from typing import List, Tuple

from application.ports import AuthorizationPort, JobRepositoryPort
from application.use_cases.dto import (
    JobDTO,
    JobsListResponseDTO,
    ListJobsRequestDTO,
    PaginationParams,
)
from domain.exceptions import AuthorizationError, ValidationError


class ListJobsUseCase:
    """Use case for listing jobs with filtering and pagination."""

    def __init__(
        self,
        job_repository: JobRepositoryPort,
        authorization_service: AuthorizationPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            job_repository: Repository for job operations
            authorization_service: Service for authorization checks
        """
        self.job_repository = job_repository
        self.authorization_service = authorization_service

    def execute(self, request: ListJobsRequestDTO) -> JobsListResponseDTO:
        """Execute the list jobs use case.

        Args:
            request: List jobs request DTO

        Returns:
            Jobs list response DTO with paginated results

        Raises:
            ValidationError: If request validation fails
            AuthorizationError: If user is not authorized
        """
        start_time = datetime.now()

        # Validate input
        self._validate_request(request)

        # Check authorization
        self._check_authorization(request)

        # Get pagination parameters
        pagination = request.pagination or PaginationParams()

        # List jobs from repository
        jobs, total_count = self._list_jobs(request, pagination)

        # Convert to DTOs
        job_dtos = [self._create_job_dto(job) for job in jobs]

        # Calculate processing time
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Create filters applied summary
        filters_applied = self._get_filters_applied(request)

        return JobsListResponseDTO(
            jobs=job_dtos,
            total_jobs=total_count,
            filters_applied=filters_applied,
            processing_time_ms=processing_time_ms,
        )

    def _validate_request(self, request: ListJobsRequestDTO) -> None:
        """Validate the list jobs request.

        Args:
            request: Request to validate

        Raises:
            ValidationError: If validation fails
        """
        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError(
                message="Tenant ID is required and cannot be empty", param="tenant_id"
            )

        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", param="user_id"
            )

        # Validate pagination if provided
        if request.pagination:
            if request.pagination.page < 1:
                raise ValidationError(
                    message="Page must be greater than or equal to 1",
                    param="pagination.page",
                )

            if request.pagination.page_size < 1 or request.pagination.page_size > 100:
                raise ValidationError(
                    message="Page size must be between 1 and 100",
                    param="pagination.page_size",
                )

        # Validate date range if provided
        if request.start_date and request.end_date:
            if request.start_date > request.end_date:
                raise ValidationError(
                    message="Start date must be before or equal to end date",
                    param="start_date",
                )

    def _check_authorization(self, request: ListJobsRequestDTO) -> None:
        """Check if user is authorized to list jobs.

        Args:
            request: Request containing user information

        Raises:
            AuthorizationError: If user is not authorized
        """
        if not self.authorization_service.check_permission(
            user_id=request.user_id,
            resource_type="job",
            action="list",
            tenant_id=request.tenant_id,
        ):
            raise AuthorizationError(
                message="User is not authorized to list jobs",
                user_id=request.user_id,
                resource_type="job",
                action="list",
            )

    def _list_jobs(
        self, request: ListJobsRequestDTO, pagination: PaginationParams
    ) -> Tuple[List, int]:
        """List jobs from the repository with filtering.

        Args:
            request: List jobs request
            pagination: Pagination parameters

        Returns:
            Tuple of (jobs list, total count)
        """
        # Check if user can see all jobs or only their own
        can_see_all_jobs = self.authorization_service.check_permission(
            user_id=request.user_id,
            resource_type="job",
            action="list_all",
            tenant_id=request.tenant_id,
        )

        # Determine created_by filter
        created_by_filter = request.created_by
        if not can_see_all_jobs:
            # User can only see their own jobs
            created_by_filter = request.user_id

        return self.job_repository.list_by_tenant(
            tenant_id=request.tenant_id,
            workflow_id=request.workflow_id,
            status=request.status,
            created_by=created_by_filter,
            start_date=request.start_date,
            end_date=request.end_date,
            page=pagination.page,
            page_size=pagination.page_size,
        )

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

    def _get_filters_applied(self, request: ListJobsRequestDTO) -> dict:
        """Get summary of filters applied.

        Args:
            request: List jobs request

        Returns:
            Dictionary of applied filters
        """
        filters = {}

        if request.workflow_id:
            filters["workflow_id"] = request.workflow_id

        if request.status:
            filters["status"] = request.status

        if request.created_by:
            filters["created_by"] = request.created_by

        if request.start_date:
            filters["start_date"] = request.start_date.isoformat()

        if request.end_date:
            filters["end_date"] = request.end_date.isoformat()

        return filters
