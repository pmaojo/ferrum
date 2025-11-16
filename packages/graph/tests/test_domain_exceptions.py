"""Unit tests for application exceptions."""

import pytest
from application.exceptions import (
    ApplicationError,
    ValidationError,
    NotFoundError,
    AuthorizationError,
    BusinessRuleViolationError,
    ConcurrencyError,
    DependencyError
)


def test_application_error_basic():
    """Test basic ApplicationError creation."""
    # Arrange & Act
    error = ApplicationError(
        message="Test error",
        error_code="TEST_ERROR",
        context={"test": "value"}
    )

    # Assert
    assert error.message == "Test error"
    assert error.error_code == "TEST_ERROR"
    assert error.context == {"test": "value"}
    assert str(error) == "Test error"


def test_validation_error():
    """Test ValidationError creation and properties."""
    # Arrange & Act
    validation_errors = [
        {"field": "name", "message": "Name is required"},
        {"field": "email", "message": "Invalid email format"}
    ]

    error = ValidationError(
        message="Validation failed",
        field="form",
        validation_errors=validation_errors,
        context={"form_id": "user_form"}
    )

    # Assert
    assert error.message == "Validation failed"
    assert error.error_code == "APPLICATION_VALIDATION_ERROR"
    assert error.field == "form"
    assert error.validation_errors == validation_errors
    assert error.context["field"] == "form"
    assert error.context["validation_errors"] == validation_errors
    assert error.context["form_id"] == "user_form"


def test_not_found_error():
    """Test NotFoundError creation and properties."""
    # Arrange & Act
    error = NotFoundError(
        message="User not found",
        resource_type="user",
        resource_id="123",
        context={"request_id": "abc"}
    )

    # Assert
    assert error.message == "User not found"
    assert error.error_code == "RESOURCE_NOT_FOUND"
    assert error.resource_type == "user"
    assert error.resource_id == "123"
    assert error.context["resource_type"] == "user"
    assert error.context["resource_id"] == "123"
    assert error.context["request_id"] == "abc"


def test_authorization_error():
    """Test AuthorizationError creation and properties."""
    # Arrange & Act
    error = AuthorizationError(
        message="Access denied",
        user_id="user123",
        resource_type="document",
        resource_id="doc456",
        required_permission="edit",
        context={"ip_address": "192.168.1.1"}
    )

    # Assert
    assert error.message == "Access denied"
    assert error.error_code == "AUTHORIZATION_ERROR"
    assert error.user_id == "user123"
    assert error.resource_type == "document"
    assert error.resource_id == "doc456"
    assert error.required_permission == "edit"
    assert error.context["user_id"] == "user123"
    assert error.context["resource_type"] == "document"
    assert error.context["resource_id"] == "doc456"
    assert error.context["required_permission"] == "edit"
    assert error.context["ip_address"] == "192.168.1.1"


def test_business_rule_violation_error():
    """Test BusinessRuleViolationError creation and properties."""
    # Arrange & Act
    error = BusinessRuleViolationError(
        message="Cannot delete active user",
        rule_name="active_user_deletion",
        context={"user_status": "active"}
    )

    # Assert
    assert error.message == "Cannot delete active user"
    assert error.error_code == "BUSINESS_RULE_VIOLATION"
    assert error.rule_name == "active_user_deletion"
    assert error.context["rule_name"] == "active_user_deletion"
    assert error.context["user_status"] == "active"


def test_concurrency_error():
    """Test ConcurrencyError creation and properties."""
    # Arrange & Act
    error = ConcurrencyError(
        message="Concurrency conflict detected",
        resource_type="document",
        resource_id="doc123",
        expected_version="v1",
        actual_version="v2",
        context={"timestamp": "2023-01-01T12:00:00Z"}
    )

    # Assert
    assert error.message == "Concurrency conflict detected"
    assert error.error_code == "CONCURRENCY_ERROR"
    assert error.resource_type == "document"
    assert error.resource_id == "doc123"
    assert error.expected_version == "v1"
    assert error.actual_version == "v2"
    assert error.context["resource_type"] == "document"
    assert error.context["resource_id"] == "doc123"
    assert error.context["expected_version"] == "v1"
    assert error.context["actual_version"] == "v2"
    assert error.context["timestamp"] == "2023-01-01T12:00:00Z"


def test_dependency_error():
    """Test DependencyError creation and properties."""
    # Arrange & Act
    error = DependencyError(
        message="Database connection failed",
        dependency_name="postgres_db",
        dependency_error="Connection timeout",
        context={"retry_count": 3}
    )

    # Assert
    assert error.message == "Database connection failed"
    assert error.error_code == "DEPENDENCY_ERROR"
    assert error.dependency_name == "postgres_db"
    assert error.dependency_error == "Connection timeout"
    assert error.context["dependency_name"] == "postgres_db"
    assert error.context["dependency_error"] == "Connection timeout"
    assert error.context["retry_count"] == 3