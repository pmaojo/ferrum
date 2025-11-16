"""Tests for CancelJobUseCase."""

import pytest
from unittest.mock import Mock

from application.use_cases.workflow.cancel_job_use_case import CancelJobUseCase
from application.use_cases.dto import CancelJobRequestDTO
from domain.entities import Job
from domain.exceptions import ValidationError
import application.use_cases.workflow.cancel_job_use_case as cancel_job_module


class TestCancelJobUseCase:
    """Test cases for CancelJobUseCase."""

    def setup_method(self):
        """Set up common test dependencies."""
        self.job_repository = Mock()
        self.workflow_execution_service = Mock()
        self.authorization_service = Mock()

        self.use_case = CancelJobUseCase(
            job_repository=self.job_repository,
            workflow_execution_service=self.workflow_execution_service,
            authorization_service=self.authorization_service,
        )

    def _create_running_job(self, job_id="job-123", tenant_id="tenant-1", user_id="user-1"):
        job = Job.create(
            workflow_id="wf-1",
            tenant_id=tenant_id,
            input_parameters={},
            created_by=user_id,
        )
        job.id = job_id
        job.start()
        return job

    def test_cancel_job_failure_rechecks_status(self):
        """When cancellation fails, the job status is re-checked and error raised."""
        request = CancelJobRequestDTO(
            tenant_id="tenant-1", user_id="user-1", job_id="job-123"
        )
        job = self._create_running_job()

        self.job_repository.get_by_id.side_effect = [job, job]
        self.authorization_service.check_permission.return_value = True
        self.workflow_execution_service.cancel_job.return_value = False

        with pytest.raises(ValidationError):
            self.use_case.execute(request)

        assert self.job_repository.get_by_id.call_count == 2
        self.job_repository.update.assert_not_called()

    def test_cancel_job_exception_propagates(self, monkeypatch):
        """Exceptions from execution service are logged and propagated."""
        request = CancelJobRequestDTO(
            tenant_id="tenant-1", user_id="user-1", job_id="job-123"
        )
        job = self._create_running_job()

        self.job_repository.get_by_id.return_value = job
        self.authorization_service.check_permission.return_value = True
        self.workflow_execution_service.cancel_job.side_effect = RuntimeError("boom")

        mock_logger = Mock()
        monkeypatch.setattr(cancel_job_module, "logger", mock_logger)

        with pytest.raises(RuntimeError):
            self.use_case.execute(request)

        mock_logger.exception.assert_called_once()
        self.job_repository.update.assert_not_called()

