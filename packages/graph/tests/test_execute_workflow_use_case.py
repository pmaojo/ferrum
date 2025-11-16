"""Tests for ExecuteWorkflowUseCase."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from application.use_cases.workflow.execute_workflow_use_case import ExecuteWorkflowUseCase
from application.use_cases.dto import ExecuteWorkflowRequestDTO, WorkflowExecutionResponseDTO
from domain.entities import Workflow, Job, WorkflowType, JobStatus
from domain.exceptions import ValidationError, AuthorizationError


class TestExecuteWorkflowUseCase:
    """Test cases for ExecuteWorkflowUseCase."""

    def setup_method(self):
        """Set up test dependencies."""
        self.workflow_repository = Mock()
        self.job_repository = Mock()
        self.workflow_execution_service = Mock()
        self.authorization_service = Mock()
        
        self.use_case = ExecuteWorkflowUseCase(
            workflow_repository=self.workflow_repository,
            job_repository=self.job_repository,
            workflow_execution_service=self.workflow_execution_service,
            authorization_service=self.authorization_service
        )

    def test_execute_success(self):
        """Test successful workflow execution."""
        # Arrange
        request = ExecuteWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            workflow_id="workflow-789",
            input_parameters={"param1": "value1"},
            max_retries=3
        )

        # Mock authorization check
        self.authorization_service.check_permission.return_value = True

        # Mock workflow retrieval
        workflow = Workflow.create(
            name="Test Workflow",
            tenant_id="tenant-123",
            definition={"steps": [{"name": "step1", "action": "process"}]},
            workflow_type=WorkflowType.INGESTION,
            created_by="user-456"
        )
        workflow.id = "workflow-789"
        self.workflow_repository.get_by_id.return_value = workflow

        # Mock job creation
        job = Job.create(
            workflow_id="workflow-789",
            tenant_id="tenant-123",
            input_parameters={"param1": "value1"},
            created_by="user-456",
            max_retries=3
        )
        job.id = "job-123"
        self.job_repository.create.return_value = job
        self.job_repository.update.return_value = job

        # Mock workflow execution
        self.workflow_execution_service.execute_workflow.return_value = {"status": "started"}

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert isinstance(result, WorkflowExecutionResponseDTO)
        assert result.execution_started is True
        assert result.message == "Workflow execution started successfully"
        assert result.job.id == "job-123"
        assert result.workflow.id == "workflow-789"

        # Verify repository calls
        self.workflow_repository.get_by_id.assert_called_once_with(
            workflow_id="workflow-789",
            tenant_id="tenant-123"
        )
        self.job_repository.create.assert_called_once()
        self.job_repository.update.assert_called()

    def test_execute_missing_workflow_id_raises_validation_error(self):
        """Test that missing workflow ID raises ValidationError."""
        # Arrange
        request = ExecuteWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            workflow_id="",  # Empty workflow ID
            input_parameters={}
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "Workflow ID is required" in str(exc_info.value)

    def test_execute_missing_tenant_id_raises_validation_error(self):
        """Test that missing tenant ID raises ValidationError."""
        # Arrange
        request = ExecuteWorkflowRequestDTO(
            tenant_id="",  # Empty tenant ID
            user_id="user-456",
            workflow_id="workflow-789",
            input_parameters={}
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "Tenant ID is required" in str(exc_info.value)

    def test_execute_missing_user_id_raises_validation_error(self):
        """Test that missing user ID raises ValidationError."""
        # Arrange
        request = ExecuteWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="",  # Empty user ID
            workflow_id="workflow-789",
            input_parameters={}
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "User ID is required" in str(exc_info.value)

    def test_execute_invalid_input_parameters_raises_validation_error(self):
        """Test that invalid input parameters raise ValidationError."""
        # Arrange
        request = ExecuteWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            workflow_id="workflow-789",
            input_parameters="invalid"  # Should be dict
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "Input parameters must be a dictionary" in str(exc_info.value)

    def test_execute_invalid_max_retries_raises_validation_error(self):
        """Test that invalid max retries raises ValidationError."""
        # Arrange
        request = ExecuteWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            workflow_id="workflow-789",
            input_parameters={},
            max_retries=-1  # Invalid negative value
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "Max retries must be a non-negative integer" in str(exc_info.value)

    def test_execute_unauthorized_user_raises_authorization_error(self):
        """Test that unauthorized user raises AuthorizationError."""
        # Arrange
        request = ExecuteWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            workflow_id="workflow-789",
            input_parameters={}
        )

        # Mock authorization check to fail
        self.authorization_service.check_permission.return_value = False

        # Act & Assert
        with pytest.raises(AuthorizationError) as exc_info:
            self.use_case.execute(request)
        
        assert "User is not authorized to execute workflows" in str(exc_info.value)

    def test_execute_workflow_not_found_raises_validation_error(self):
        """Test that workflow not found raises ValidationError."""
        # Arrange
        request = ExecuteWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            workflow_id="nonexistent-workflow",
            input_parameters={}
        )

        # Mock authorization check
        self.authorization_service.check_permission.return_value = True

        # Mock workflow not found
        self.workflow_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "Workflow with ID nonexistent-workflow not found" in str(exc_info.value)

    def test_execute_inactive_workflow_raises_validation_error(self):
        """Test that inactive workflow raises ValidationError."""
        # Arrange
        request = ExecuteWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            workflow_id="workflow-789",
            input_parameters={}
        )

        # Mock authorization check
        self.authorization_service.check_permission.return_value = True

        # Mock inactive workflow
        workflow = Workflow.create(
            name="Test Workflow",
            tenant_id="tenant-123",
            definition={"steps": []},
            workflow_type=WorkflowType.INGESTION,
            created_by="user-456"
        )
        workflow.id = "workflow-789"
        workflow.deactivate()  # Make it inactive
        self.workflow_repository.get_by_id.return_value = workflow

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "Workflow with ID workflow-789 is not active" in str(exc_info.value)

    def test_execute_workflow_execution_failure(self):
        """Test workflow execution failure handling."""
        # Arrange
        request = ExecuteWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            workflow_id="workflow-789",
            input_parameters={"param1": "value1"}
        )

        # Mock authorization check
        self.authorization_service.check_permission.return_value = True

        # Mock workflow retrieval
        workflow = Workflow.create(
            name="Test Workflow",
            tenant_id="tenant-123",
            definition={"steps": []},
            workflow_type=WorkflowType.INGESTION,
            created_by="user-456"
        )
        workflow.id = "workflow-789"
        self.workflow_repository.get_by_id.return_value = workflow

        # Mock job creation
        job = Job.create(
            workflow_id="workflow-789",
            tenant_id="tenant-123",
            input_parameters={"param1": "value1"},
            created_by="user-456"
        )
        job.id = "job-123"
        self.job_repository.create.return_value = job
        self.job_repository.update.return_value = job

        # Mock workflow execution failure
        self.workflow_execution_service.execute_workflow.side_effect = Exception("Execution failed")

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.execution_started is False
        assert result.message == "Failed to start workflow execution"
        
        # Verify job was marked as failed
        self.job_repository.update.assert_called()

    def test_execute_with_default_parameters(self):
        """Test workflow execution with default parameters."""
        # Arrange
        request = ExecuteWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            workflow_id="workflow-789"
            # input_parameters and max_retries use defaults
        )

        # Mock authorization check
        self.authorization_service.check_permission.return_value = True

        # Mock workflow retrieval
        workflow = Workflow.create(
            name="Test Workflow",
            tenant_id="tenant-123",
            definition={"steps": []},
            workflow_type=WorkflowType.INGESTION,
            created_by="user-456"
        )
        workflow.id = "workflow-789"
        self.workflow_repository.get_by_id.return_value = workflow

        # Mock job creation
        job = Job.create(
            workflow_id="workflow-789",
            tenant_id="tenant-123",
            input_parameters={},
            created_by="user-456",
            max_retries=3
        )
        job.id = "job-123"
        self.job_repository.create.return_value = job
        self.job_repository.update.return_value = job

        # Mock workflow execution
        self.workflow_execution_service.execute_workflow.return_value = {"status": "started"}

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.execution_started is True
        assert result.job.input_parameters == {}
        assert result.job.max_retries == 3

    def test_execute_creates_correct_job_dto(self):
        """Test that the correct job DTO is created."""
        # Arrange
        request = ExecuteWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            workflow_id="workflow-789",
            input_parameters={"param1": "value1"},
            max_retries=5
        )

        # Mock authorization check
        self.authorization_service.check_permission.return_value = True

        # Mock workflow retrieval
        workflow = Workflow.create(
            name="Test Workflow",
            tenant_id="tenant-123",
            definition={"steps": []},
            workflow_type=WorkflowType.ANALYTICS,
            created_by="user-456"
        )
        workflow.id = "workflow-789"
        self.workflow_repository.get_by_id.return_value = workflow

        # Mock job creation
        job = Job.create(
            workflow_id="workflow-789",
            tenant_id="tenant-123",
            input_parameters={"param1": "value1"},
            created_by="user-456",
            max_retries=5
        )
        job.id = "job-123"
        job.start()  # Mark as started
        self.job_repository.create.return_value = job
        self.job_repository.update.return_value = job

        # Mock workflow execution
        self.workflow_execution_service.execute_workflow.return_value = {"status": "started"}

        # Act
        result = self.use_case.execute(request)

        # Assert
        job_dto = result.job
        assert job_dto.id == "job-123"
        assert job_dto.workflow_id == "workflow-789"
        assert job_dto.tenant_id == "tenant-123"
        assert job_dto.status == "running"  # Should be lowercase
        assert job_dto.input_parameters == {"param1": "value1"}
        assert job_dto.created_by == "user-456"
        assert job_dto.max_retries == 5

        workflow_dto = result.workflow
        assert workflow_dto.id == "workflow-789"
        assert workflow_dto.name == "Test Workflow"
        assert workflow_dto.workflow_type == "analytics"  # Should be lowercase