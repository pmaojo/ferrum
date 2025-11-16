"""Application layer exceptions for GraphRAG Ontology Application.

This module defines typed exceptions for the application layer, providing
structured error handling and consistent error reporting for use cases.
"""

from typing import Any, Dict, List, Optional

from domain.exceptions import GraphRAGException


class ApplicationError(GraphRAGException):
    """Base exception for application layer errors."""

    def __init__(
        self, message: str, error_code: str, context: Optional[Dict[str, Any]] = None
    ):
        """Initialize ApplicationError.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            context: Optional context information for debugging
        """
        super().__init__(message=message, error_code=error_code, context=context)


class ValidationError(ApplicationError):
    """Exception raised when use case input validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        validation_errors: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize ValidationError.

        Args:
            message: Human-readable error message
            field: Optional field that failed validation
            validation_errors: Optional list of detailed validation errors
            context: Optional context information for debugging
        """
        self.field = field
        self.validation_errors = validation_errors or []

        super().__init__(
            message=message,
            error_code="APPLICATION_VALIDATION_ERROR",
            context={
                "field": field,
                "validation_errors": validation_errors,
                **(context or {}),
            },
        )


class NotFoundError(ApplicationError):
    """Exception raised when a requested resource is not found."""

    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_id: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize NotFoundError.

        Args:
            message: Human-readable error message
            resource_type: Type of resource that was not found
            resource_id: Identifier of the resource
            context: Optional context information for debugging
        """
        self.resource_type = resource_type
        self.resource_id = resource_id

        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            context={
                "resource_type": resource_type,
                "resource_id": resource_id,
                **(context or {}),
            },
        )


class AuthorizationError(ApplicationError):
    """Exception raised when a user is not authorized to perform an action."""

    def __init__(
        self,
        message: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        required_permission: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize AuthorizationError.

        Args:
            message: Human-readable error message
            user_id: Optional identifier of the user
            resource_type: Optional type of resource being accessed
            resource_id: Optional identifier of the resource
            required_permission: Optional permission that was required
            context: Optional context information for debugging
        """
        self.user_id = user_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.required_permission = required_permission

        base_context = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "required_permission": required_permission,
        }
        if user_id is not None:
            base_context["user_id"] = user_id

        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            context={**base_context, **(context or {})},
        )


class BusinessRuleViolationError(ApplicationError):
    """Exception raised when a business rule is violated."""

    def __init__(
        self, message: str, rule_name: str, context: Optional[Dict[str, Any]] = None
    ):
        """Initialize BusinessRuleViolationError.

        Args:
            message: Human-readable error message
            rule_name: Name of the business rule that was violated
            context: Optional context information for debugging
        """
        self.rule_name = rule_name

        super().__init__(
            message=message,
            error_code="BUSINESS_RULE_VIOLATION",
            context={"rule_name": rule_name, **(context or {})},
        )


class ConcurrencyError(ApplicationError):
    """Exception raised when a concurrency conflict occurs."""

    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_id: str,
        expected_version: Optional[str] = None,
        actual_version: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize ConcurrencyError.

        Args:
            message: Human-readable error message
            resource_type: Type of resource with concurrency conflict
            resource_id: Identifier of the resource
            expected_version: Optional version that was expected
            actual_version: Optional version that was found
            context: Optional context information for debugging
        """
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.expected_version = expected_version
        self.actual_version = actual_version

        super().__init__(
            message=message,
            error_code="CONCURRENCY_ERROR",
            context={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "expected_version": expected_version,
                "actual_version": actual_version,
                **(context or {}),
            },
        )


class DependencyError(ApplicationError):
    """Exception raised when a dependency is not available or fails."""

    def __init__(
        self,
        message: str,
        dependency_name: str,
        dependency_error: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize DependencyError.

        Args:
            message: Human-readable error message
            dependency_name: Name of the dependency that failed
            dependency_error: Optional error message from the dependency
            context: Optional context information for debugging
        """
        self.dependency_name = dependency_name
        self.dependency_error = dependency_error

        super().__init__(
            message=message,
            error_code="DEPENDENCY_ERROR",
            context={
                "dependency_name": dependency_name,
                "dependency_error": dependency_error,
                **(context or {}),
            },
        )


class ProgressUpdateError(ApplicationError):
    """Exception raised when job progress retrieval fails."""

    def __init__(
        self,
        *,
        job_id: str,
        tenant_id: str,
        cause: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize ProgressUpdateError.

        Args:
            job_id: Identifier of the job being updated
            tenant_id: Tenant owning the job
            cause: Original exception from the progress service
            context: Optional context information for debugging
        """
        self.job_id = job_id
        self.tenant_id = tenant_id
        self.cause = cause

        base_context: Dict[str, Any] = {"job_id": job_id, "tenant_id": tenant_id}
        if cause is not None:
            base_context["cause"] = str(cause)

        super().__init__(
            message=f"Failed to update progress for job {job_id}",
            error_code="PROGRESS_UPDATE_FAILED",
            context={**base_context, **(context or {})},
        )
