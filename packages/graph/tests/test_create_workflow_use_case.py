"""Tests for CreateWorkflowUseCase."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from application.use_cases.workflow.create_workflow_use_case import CreateWorkflowUseCase
from application.use_cases.dto import CreateWorkflowRequestDTO, WorkflowDTO
from domain.entities import Workflow, WorkflowType
from domain.exceptions import ValidationError, AuthorizationError


class TestCreateWorkflowUseCase:
    """Test cases for CreateWorkflowUseCase."""

    def setup_method(self):
        """Set up test dependencies."""
        self.workflow_repository = Mock()
        self.workflow_validator = Mock()
        self.authorization_service = Mock()
        
        self.use_case = CreateWorkflowUseCase(
            workflow_repository=self.workflow_repository,
            workflow_validator=self.workflow_validator,
            authorization_service=self.authorization_service
        )

    def test_execute_success(self):
        """Test successful workflow creation."""
        # Arrange
        request = CreateWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Test Workflow",
            description="A test workflow",
            definition={"steps": [{"name": "step1", "action": "process"}]},
            workflow_type="ingestion",
            version="1.0.0"
        )

        # Mock authorization check
        self.authorization_service.check_permission.return_value = True

        # Mock workflow validation
        self.workflow_validator.validate_workflow_definition.return_value = (True, [])

        # Mock workflow creation
        created_workflow = Workflow.create(
            name="Test Workflow",
            tenant_id="tenant-123",
            definition={"steps": [{"name": "step1", "action": "process"}]},
            workflow_type=WorkflowType.INGESTION,
            created_by="user-456",
            description="A test workflow",
            version="1.0.0"
        )
        self.workflow_repository.create.return_value = created_workflow

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert isinstance(result, WorkflowDTO)
        assert result.name == "Test Workflow"
        assert result.description == "A test workflow"
        assert result.tenant_id == "tenant-123"
        assert result.workflow_type == "ingestion"
        assert result.version == "1.0.0"
        assert result.created_by == "user-456"
        assert result.is_active is True

        # Verify repository was called
        self.workflow_repository.create.assert_called_once()
        created_arg = self.workflow_repository.create.call_args[0][0]
        assert isinstance(created_arg, Workflow)
        assert created_arg.name == "Test Workflow"

    def test_execute_missing_name_raises_validation_error(self):
        """Test that missing name raises ValidationError."""
        # Arrange
        request = CreateWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="",  # Empty name
            description="Test description",
            definition={"steps": []},
            workflow_type="ingestion"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "Workflow name is required" in str(exc_info.value)

    def test_execute_missing_tenant_id_raises_validation_error(self):
        """Test that missing tenant ID raises ValidationError."""
        # Arrange
        request = CreateWorkflowRequestDTO(
            tenant_id="",  # Empty tenant ID
            user_id="user-456",
            name="Test Workflow",
            description="Test description",
            definition={"steps": []},
            workflow_type="ingestion"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "Tenant ID is required" in str(exc_info.value)

    def test_execute_missing_user_id_raises_validation_error(self):
        """Test that missing user ID raises ValidationError."""
        # Arrange
        request = CreateWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="",  # Empty user ID
            name="Test Workflow",
            description="Test description",
            definition={"steps": []},
            workflow_type="ingestion"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "User ID is required" in str(exc_info.value)

    def test_execute_invalid_definition_raises_validation_error(self):
        """Test that invalid definition raises ValidationError."""
        # Arrange
        request = CreateWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Test Workflow",
            description="Test description",
            definition=None,  # Invalid definition
            workflow_type="ingestion"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "Workflow definition is required" in str(exc_info.value)

    def test_execute_invalid_workflow_type_raises_validation_error(self):
        """Test that invalid workflow type raises ValidationError."""
        # Arrange
        request = CreateWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Test Workflow",
            description="Test description",
            definition={"steps": []},
            workflow_type="invalid_type"  # Invalid workflow type
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "Workflow type must be one of" in str(exc_info.value)

    def test_execute_unauthorized_user_raises_authorization_error(self):
        """Test that unauthorized user raises AuthorizationError."""
        # Arrange
        request = CreateWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Test Workflow",
            description="Test description",
            definition={"steps": []},
            workflow_type="ingestion"
        )

        # Mock authorization check to fail
        self.authorization_service.check_permission.return_value = False

        # Act & Assert
        with pytest.raises(AuthorizationError) as exc_info:
            self.use_case.execute(request)
        
        assert "User is not authorized to create workflows" in str(exc_info.value)

    def test_execute_invalid_workflow_definition_raises_validation_error(self):
        """Test that invalid workflow definition raises ValidationError."""
        # Arrange
        request = CreateWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Test Workflow",
            description="Test description",
            definition={"invalid": "definition"},
            workflow_type="ingestion"
        )

        # Mock authorization check
        self.authorization_service.check_permission.return_value = True

        # Mock workflow validation to fail
        self.workflow_validator.validate_workflow_definition.return_value = (
            False, 
            ["Missing required field: steps", "Invalid action type"]
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)
        
        assert "Workflow definition validation failed" in str(exc_info.value)
        assert "Missing required field: steps" in str(exc_info.value)

    def test_execute_all_workflow_types_valid(self):
        """Test that all valid workflow types are accepted."""
        valid_types = ["ingestion", "query", "analytics", "export", "validation", "transformation"]
        
        for workflow_type in valid_types:
            # Arrange
            request = CreateWorkflowRequestDTO(
                tenant_id="tenant-123",
                user_id="user-456",
                name="Test Workflow",
                description="Test description",
                definition={"steps": []},
                workflow_type=workflow_type
            )

            # Mock authorization and validation
            self.authorization_service.check_permission.return_value = True
            self.workflow_validator.validate_workflow_definition.return_value = (True, [])

            # Mock workflow creation
            created_workflow = Workflow.create(
                name="Test Workflow",
                tenant_id="tenant-123",
                definition={"steps": []},
                workflow_type=WorkflowType(workflow_type.lower()),
                created_by="user-456"
            )
            self.workflow_repository.create.return_value = created_workflow

            # Act
            result = self.use_case.execute(request)

            # Assert
            assert result.workflow_type == workflow_type

    def test_execute_with_optional_description(self):
        """Test workflow creation with optional description."""
        # Arrange
        request = CreateWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Test Workflow",
            description=None,  # No description
            definition={"steps": []},
            workflow_type="ingestion"
        )

        # Mock dependencies
        self.authorization_service.check_permission.return_value = True
        self.workflow_validator.validate_workflow_definition.return_value = (True, [])

        created_workflow = Workflow.create(
            name="Test Workflow",
            tenant_id="tenant-123",
            definition={"steps": []},
            workflow_type=WorkflowType.INGESTION,
            created_by="user-456",
            description=None
        )
        self.workflow_repository.create.return_value = created_workflow

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.description is None

    def test_execute_strips_whitespace_from_inputs(self):
        """Test that whitespace is stripped from string inputs."""
        # Arrange
        request = CreateWorkflowRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="  Test Workflow  ",  # With whitespace
            description="  A test workflow  ",  # With whitespace
            definition={"steps": []},
            workflow_type="ingestion",
            version="  1.0.0  "  # With whitespace
        )

        # Mock dependencies
        self.authorization_service.check_permission.return_value = True
        self.workflow_validator.validate_workflow_definition.return_value = (True, [])

        created_workflow = Workflow.create(
            name="Test Workflow",
            tenant_id="tenant-123",
            definition={"steps": []},
            workflow_type=WorkflowType.INGESTION,
            created_by="user-456",
            description="A test workflow",
            version="1.0.0"
        )
        self.workflow_repository.create.return_value = created_workflow

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.name == "Test Workflow"
        assert result.description == "A test workflow"
        assert result.version == "1.0.0"