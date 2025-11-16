"""Tests for GetJobStatusUseCase."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from application.use_cases.workflow.get_job_status_use_case import GetJobStatusUseCase
from application.use_cases.dto import GetJobStatusRequestDTO, JobDTO
from domain.entities import Job, JobStatus
from domain.exceptions import ValidationError, AuthorizationError
from application.exceptions import ProgressUpdateError


class TestGetJobStatusUseCase:
    """Test cases for GetJobStatusUseCase."""

    def setup_method(self):
        """Set up test dependencies."""
        self.job_repository = Mock()
        self.workflow_execution_service = Mock()
        self.authorization_service = Mock()
        
        self.use_case = GetJobStatusUseCase(
            job_repository=self.job_repository,
            workflow_execution_service=self.workflow_execution_service,
            authorization_service=self.authorization_service
        )

    def test_execute_success(self):
        """Test successful job status retrieval."""
        # Arrange
        request = GetJobStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            job_id="job-789"
        )

        # Mock job retrieval
        job = Job.create(
            workflow_id="workflow-123",
            tenant_id="tenant-123",
            input_parameters={"param1": "value1"},
            created_by="user-456"
        )
        job.id = "job-789"
        job.start()  # Mark as running
        self.job_repository.get_by_id.return_value = job

        # Mock authorization checks
        self.authorization_service.check_permission.return_value = True

        # Mock progress update (no update needed)
        self.workflow_execution_service.get_job_progress.return_value = None

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert isinstance(result, JobDTO)
        assert result.id == "job-789"
        assert result.workflow_id == "workflow-123"
        assert result.tenant_id == "tenant-123"
        assert result.status == "running"
        assert result.created_by == "user-456"

        # Verify repository calls
        self.job_repository.get_by_id.assert_called_once_with(
            job_id="job-789",
            tenant_id="tenant-123"
        )

    def test_execute_missing_job_id_raises_validation_error(self):
        """Test that missing job ID raises ValidationError."""
        # Arrange
        request = GetJobStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            job_id=""  # Empty job ID
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "Job ID is required" in str(exc_info.value)

    def test_execute_missing_tenant_id_raises_validation_error(self):
        """Test that missing tenant ID raises ValidationError."""
        # Arrange
        request = GetJobStatusRequestDTO(
            tenant_id="",  # Empty tenant ID
            user_id="user-456",
            job_id="job-789"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "Tenant ID is required" in str(exc_info.value)

    def test_execute_missing_user_id_raises_validation_error(self):
        """Test that missing user ID raises ValidationError."""
        # Arrange
        request = GetJobStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="",  # Empty user ID
            job_id="job-789"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "User ID is required" in str(exc_info.value)

    def test_execute_job_not_found_raises_validation_error(self):
        """Test that job not found raises ValidationError."""
        # Arrange
        request = GetJobStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            job_id="nonexistent-job"
        )

        # Mock job not found
        self.job_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "Job with ID nonexistent-job not found" in str(exc_info.value)

    def test_execute_unauthorized_user_raises_authorization_error(self):
        """Test that unauthorized user raises AuthorizationError."""
        # Arrange
        request = GetJobStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            job_id="job-789"
        )

        # Mock job retrieval
        job = Job.create(
            workflow_id="workflow-123",
            tenant_id="tenant-123",
            input_parameters={},
            created_by="user-456"
        )
        job.id = "job-789"
        self.job_repository.get_by_id.return_value = job

        # Mock authorization check to fail
        self.authorization_service.check_permission.return_value = False

        # Act & Assert
        with pytest.raises(AuthorizationError) as exc_info:
            self.use_case.execute(request)
        
        assert "User is not authorized to view job status" in str(exc_info.value)

    def test_execute_user_cannot_view_other_users_job(self):
        """Test that user cannot view another user's job without admin permissions."""
        # Arrange
        request = GetJobStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            job_id="job-789"
        )

        # Mock job retrieval (created by different user)
        job = Job.create(
            workflow_id="workflow-123",
            tenant_id="tenant-123",
            input_parameters={},
            created_by="other-user"  # Different user
        )
        job.id = "job-789"
        self.job_repository.get_by_id.return_value = job

        # Mock authorization checks
        def mock_check_permission(user_id, resource_type, action, tenant_id):
            if action == "read":
                return True  # Can read jobs in general
            elif action == "read_all":
                return False  # Cannot read all jobs (no admin permission)
            return False

        self.authorization_service.check_permission.side_effect = mock_check_permission

        # Act & Assert
        with pytest.raises(AuthorizationError) as exc_info:
            self.use_case.execute(request)
        
        assert "User is not authorized to view this job" in str(exc_info.value)

    def test_execute_admin_can_view_any_job(self):
        """Test that admin user can view any job."""
        # Arrange
        request = GetJobStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="admin-user",
            job_id="job-789"
        )

        # Mock job retrieval (created by different user)
        job = Job.create(
            workflow_id="workflow-123",
            tenant_id="tenant-123",
            input_parameters={},
            created_by="other-user"  # Different user
        )
        job.id = "job-789"
        self.job_repository.get_by_id.return_value = job

        # Mock authorization checks (admin has read_all permission)
        def mock_check_permission(user_id, resource_type, action, tenant_id):
            return True  # Admin can do everything

        self.authorization_service.check_permission.side_effect = mock_check_permission

        # Mock progress update
        self.workflow_execution_service.get_job_progress.return_value = None

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.id == "job-789"
        assert result.created_by == "other-user"

    def test_execute_updates_running_job_progress(self):
        """Test that running job progress is updated."""
        # Arrange
        request = GetJobStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            job_id="job-789"
        )

        # Mock running job
        job = Job.create(
            workflow_id="workflow-123",
            tenant_id="tenant-123",
            input_parameters={},
            created_by="user-456"
        )
        job.id = "job-789"
        job.start()  # Mark as running
        self.job_repository.get_by_id.return_value = job
        self.job_repository.update.return_value = job

        # Mock authorization checks
        self.authorization_service.check_permission.return_value = True

        # Mock progress update
        self.workflow_execution_service.get_job_progress.return_value = {
            "progress_percentage": 75.0,
            "message": "Processing data..."
        }

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.progress_percentage == 75.0
        self.job_repository.update.assert_called_once()

    def test_execute_updates_completed_job_status(self):
        """Test that job status is updated when completed."""
        # Arrange
        request = GetJobStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            job_id="job-789"
        )

        # Mock running job
        job = Job.create(
            workflow_id="workflow-123",
            tenant_id="tenant-123",
            input_parameters={},
            created_by="user-456"
        )
        job.id = "job-789"
        job.start()  # Mark as running
        self.job_repository.get_by_id.return_value = job
        self.job_repository.update.return_value = job

        # Mock authorization checks
        self.authorization_service.check_permission.return_value = True

        # Mock progress update showing completion
        self.workflow_execution_service.get_job_progress.return_value = {
            "status": "completed",
            "progress_percentage": 100.0,
            "output_data": {"result": "success"}
        }

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.status == "completed"
        assert result.progress_percentage == 100.0
        self.job_repository.update.assert_called_once()

    def test_execute_updates_failed_job_status(self):
        """Test that job status is updated when failed."""
        # Arrange
        request = GetJobStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            job_id="job-789"
        )

        # Mock running job
        job = Job.create(
            workflow_id="workflow-123",
            tenant_id="tenant-123",
            input_parameters={},
            created_by="user-456"
        )
        job.id = "job-789"
        job.start()  # Mark as running
        self.job_repository.get_by_id.return_value = job
        self.job_repository.update.return_value = job

        # Mock authorization checks
        self.authorization_service.check_permission.return_value = True

        # Mock progress update showing failure
        self.workflow_execution_service.get_job_progress.return_value = {
            "status": "failed",
            "error_message": "Processing failed due to invalid input"
        }

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.status == "failed"
        assert result.error_message == "Processing failed due to invalid input"
        self.job_repository.update.assert_called_once()

    def test_execute_progress_update_failure_raises_error(self):
        """Test that progress update failures raise ProgressUpdateError."""
        # Arrange
        request = GetJobStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            job_id="job-789"
        )

        # Mock running job
        job = Job.create(
            workflow_id="workflow-123",
            tenant_id="tenant-123",
            input_parameters={},
            created_by="user-456"
        )
        job.id = "job-789"
        job.start()  # Mark as running
        self.job_repository.get_by_id.return_value = job

        # Mock authorization checks
        self.authorization_service.check_permission.return_value = True

        # Mock progress update to raise exception
        self.workflow_execution_service.get_job_progress.side_effect = Exception("Service unavailable")

        # Act & Assert
        with pytest.raises(ProgressUpdateError):
            self.use_case.execute(request)

    def test_execute_does_not_update_non_running_job(self):
        """Test that non-running jobs are not updated."""
        # Arrange
        request = GetJobStatusRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            job_id="job-789"
        )

        # Mock completed job
        job = Job.create(
            workflow_id="workflow-123",
            tenant_id="tenant-123",
            input_parameters={},
            created_by="user-456"
        )
        job.id = "job-789"
        job.complete({"result": "success"})  # Mark as completed
        self.job_repository.get_by_id.return_value = job

        # Mock authorization checks
        self.authorization_service.check_permission.return_value = True

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.status == "completed"
        # Progress service should not be called for non-running jobs
        self.workflow_execution_service.get_job_progress.assert_not_called()
        self.job_repository.update.assert_not_called()
