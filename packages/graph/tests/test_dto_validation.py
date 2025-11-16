"""Unit tests for DTO validation."""

import pytest
from datetime import datetime
from typing import List

from application.use_cases.dto import (
    PaginationParams,
    SortDirection,
    SortParams,
    PaginatedRequest,
    PaginatedResponse,
    BaseResponseDTO,
    ErrorResponseDTO,
    ValidationErrorDetail,
    ValidationErrorResponseDTO,
    IdResponseDTO,
    BulkOperationResponseDTO,
    AuditInfoDTO,
    TenantScopedRequestDTO
)


def test_pagination_params_valid():
    """Test valid pagination parameters."""
    # Arrange & Act
    params = PaginationParams(page=2, page_size=30)

    # Assert
    assert params.page == 2
    assert params.page_size == 30


def test_pagination_params_default():
    """Test default pagination parameters."""
    # Arrange & Act
    params = PaginationParams()

    # Assert
    assert params.page == 1
    assert params.page_size == 20


def test_pagination_params_invalid_page():
    """Test invalid page number."""
    # Arrange & Act & Assert
    with pytest.raises(ValueError) as exc_info:
        PaginationParams(page=0)

    assert "Page must be greater than or equal to 1" in str(exc_info.value)


def test_pagination_params_invalid_page_size_low():
    """Test invalid page size (too low)."""
    # Arrange & Act & Assert
    with pytest.raises(ValueError) as exc_info:
        PaginationParams(page_size=0)

    assert "Page size must be greater than or equal to 1" in str(exc_info.value)


def test_pagination_params_invalid_page_size_high():
    """Test invalid page size (too high)."""
    # Arrange & Act & Assert
    with pytest.raises(ValueError) as exc_info:
        PaginationParams(page_size=101)

    assert "Page size must be less than or equal to 100" in str(exc_info.value)


def test_sort_params():
    """Test sort parameters."""
    # Arrange & Act
    params = SortParams(sort_by="name", direction=SortDirection.DESC)

    # Assert
    assert params.sort_by == "name"
    assert params.direction == SortDirection.DESC


def test_sort_direction_enum():
    """Test sort direction enum values."""
    # Assert
    assert SortDirection.ASC == "asc"
    assert SortDirection.DESC == "desc"


def test_paginated_request():
    """Test paginated request."""
    # Arrange & Act
    pagination = PaginationParams(page=2, page_size=15)
    sort = SortParams(sort_by="created_at", direction=SortDirection.DESC)
    request = PaginatedRequest(pagination=pagination, sort=sort)

    # Assert
    assert request.pagination == pagination
    assert request.sort == sort
    assert request.filters is None


def test_paginated_response():
    """Test paginated response."""
    # Arrange & Act
    items = ["item1", "item2", "item3"]
    response = PaginatedResponse(
        items=items,
        total_items=23,
        total_pages=8,
        page=2,
        page_size=3,
        has_next_page=True,
        has_previous_page=True
    )

    # Assert
    assert response.items == items
    assert response.total_items == 23
    assert response.total_pages == 8
    assert response.page == 2
    assert response.page_size == 3
    assert response.has_next_page is True
    assert response.has_previous_page is True


def test_base_response_dto():
    """Test base response DTO."""
    # Arrange & Act
    now = datetime.now()
    response = BaseResponseDTO(
        success=True,
        processing_time_ms=42.5,
        timestamp=now
    )

    # Assert
    assert response.success is True
    assert response.processing_time_ms == 42.5
    assert response.error_message is None
    assert response.timestamp == now


def test_error_response_dto():
    """Test error response DTO."""
    # Arrange & Act
    now = datetime.now()
    response = ErrorResponseDTO(
        error_code="NOT_FOUND",
        error_message="Resource not found",
        details={"resource_id": "123"},
        timestamp=now
    )

    # Assert
    assert response.error_code == "NOT_FOUND"
    assert response.error_message == "Resource not found"
    assert response.details == {"resource_id": "123"}
    assert response.timestamp == now


def test_validation_error_detail():
    """Test validation error detail."""
    # Arrange & Act
    detail = ValidationErrorDetail(
        field="email",
        message="Invalid email format",
        code="invalid_format",
        value="not-an-email"
    )

    # Assert
    assert detail.field == "email"
    assert detail.message == "Invalid email format"
    assert detail.code == "invalid_format"
    assert detail.value == "not-an-email"


def test_validation_error_response_dto():
    """Test validation error response DTO."""
    # Arrange & Act
    details = [
        ValidationErrorDetail(field="email", message="Invalid email", code="invalid_format"),
        ValidationErrorDetail(field="name", message="Required", code="required")
    ]

    response = ValidationErrorResponseDTO(
        error_code="VALIDATION_ERROR",
        error_message="Validation failed",
        validation_errors=details
    )

    # Assert
    assert response.error_code == "VALIDATION_ERROR"
    assert response.error_message == "Validation failed"
    assert len(response.validation_errors) == 2
    assert response.validation_errors[0].field == "email"
    assert response.validation_errors[1].field == "name"


def test_id_response_dto():
    """Test ID response DTO."""
    # Arrange & Act
    response = IdResponseDTO(id="abc123")

    # Assert
    assert response.id == "abc123"
    assert response.success is True


def test_bulk_operation_response_dto():
    """Test bulk operation response DTO."""
    # Arrange & Act
    success_ids = ["id1", "id2"]
    failure_details = [
        {"id": "id3", "error": "Not found"},
        {"id": "id4", "error": "Permission denied"}
    ]

    response = BulkOperationResponseDTO(
        success_count=2,
        failure_count=2,
        total_count=4,
        success_ids=success_ids,
        failure_details=failure_details
    )

    # Assert
    assert response.success_count == 2
    assert response.failure_count == 2
    assert response.total_count == 4
    assert response.success_ids == success_ids
    assert response.failure_details == failure_details
    assert response.success is True


def test_audit_info_dto():
    """Test audit info DTO."""
    # Arrange & Act
    created_at = datetime.now()
    updated_at = datetime.now()

    audit = AuditInfoDTO(
        created_at=created_at,
        created_by="user1",
        updated_at=updated_at,
        updated_by="user2"
    )

    # Assert
    assert audit.created_at == created_at
    assert audit.created_by == "user1"
    assert audit.updated_at == updated_at
    assert audit.updated_by == "user2"


def test_tenant_scoped_request_dto():
    """Test tenant scoped request DTO."""
    # Arrange & Act
    request = TenantScopedRequestDTO(
        tenant_id="tenant123",
        user_id="user456"
    )

    # Assert
    assert request.tenant_id == "tenant123"
    assert request.user_id == "user456"