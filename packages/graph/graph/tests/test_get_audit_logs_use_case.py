"""Tests for the get audit logs use case."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from application.exceptions import ValidationError, AuthorizationError, ApplicationError
from application.ports.audit import AuditLogFilter, AuditLogSeverity, AuditLogCategory
from application.use_cases.dto import PaginationParams
from application.use_cases.system.get_audit_logs_use_case import (
    GetAuditLogsUseCase,
    GetAuditLogsRequest,
    GetAuditLogsResponse,
    AuditLogDTO,
)


class TestGetAuditLogsUseCase:
    """Test suite for the get audit logs use case."""

    def setup_method(self):
        """Set up test dependencies."""
        self.audit_repository = Mock()
        self.authorization_port = Mock()
        self.tracer = Mock()

        # Mock tracer span
        self.mock_span = Mock()
        self.tracer.start_span.return_value.__enter__ = Mock(return_value=self.mock_span)
        self.tracer.start_span.return_value.__exit__ = Mock(return_value=None)

        self.use_case = GetAuditLogsUseCase(
            audit_repository=self.audit_repository,
            authorization_port=self.authorization_port,
            tracer=self.tracer,
        )

        # Sample audit log data
        self.now = datetime.utcnow()
        self.sample_logs = [
            {
                "id": "log1",
                "tenant_id": "tenant1",
                "user_id": "user1",
                "action": "create",
                "resource_type": "knowledge_graph",
                "resource_id": "kg1",
                "severity": "info",
                "category": "data_modification",
                "details": {"name": "Test Graph"},
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0",
                "session_id": "session1",
                "timestamp": self.now - timedelta(hours=1)
            },
            {
                "id": "log2",
                "tenant_id": "tenant1",
                "user_id": "user2",
                "action": "update",
                "resource_type": "knowledge_graph",
                "resource_id": "kg1",
                "severity": "info",
                "category": "data_modification",
                "details": {"name": "Updated Graph"},
                "ip_address": "192.168.1.2",
                "user_agent": "Mozilla/5.0",
                "session_id": "session2",
                "timestamp": self.now - timedelta(minutes=30)
            },
            {
                "id": "log3",
                "tenant_id": "tenant1",
                "user_id": "admin1",
                "action": "delete",
                "resource_type": "user",
                "resource_id": "user3",
                "severity": "warning",
                "category": "user_management",
                "details": {"reason": "Account inactive"},
                "ip_address": "192.168.1.3",
                "user_agent": "Mozilla/5.0",
                "session_id": "session3",
                "timestamp": self.now - timedelta(minutes=15)
            }
        ]
        
        self.sample_summary = {
            "total": 3,
            "by_severity": {"info": 2, "warning": 1},
            "by_category": {"data_modification": 2, "user_management": 1},
            "by_action": {"create": 1, "update": 1, "delete": 1}
        }

    @pytest.fixture
    def anyio_backend(self):
        return "asyncio"

    @pytest.mark.anyio
    async def test_get_audit_logs_success(self):
        """Test successful audit logs retrieval."""
        # Arrange
        request = GetAuditLogsRequest(
            user_id="admin1",
            tenant_id="tenant1",
            pagination=PaginationParams(page=1, page_size=10)
        )

        self.audit_repository.get_logs.return_value = (self.sample_logs, 3)

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert len(response.logs) == 3
        assert response.total_count == 3
        
        # Check that logs are converted to DTOs correctly
        assert response.logs[0].id == "log1"
        assert response.logs[0].action == "create"
        assert response.logs[0].resource_type == "knowledge_graph"
        
        # Check that repository was called with correct parameters
        self.audit_repository.get_logs.assert_called_once()
        call_args = self.audit_repository.get_logs.call_args[1]
        assert call_args["page"] == 1
        assert call_args["page_size"] == 10
        assert isinstance(call_args["filter_criteria"], AuditLogFilter)
        assert call_args["filter_criteria"].tenant_id == "tenant1"
        
        self.authorization_port.check_permission.assert_called_once_with(
            user_id="admin1",
            resource_type="audit_logs",
            permission="view_audit_logs"
        )
        
        self.tracer.record_metric.assert_called_with(
            name="audit_logs_query",
            value=1,
            log_count=3,
            total_count=3
        )

    @pytest.mark.anyio
    async def test_get_audit_logs_with_filters(self):
        """Test audit logs retrieval with filters."""
        # Arrange
        request = GetAuditLogsRequest(
            user_id="admin1",
            tenant_id="tenant1",
            resource_type="knowledge_graph",
            action="create",
            severity="info",
            category="data_modification",
            start_time=self.now - timedelta(hours=2),
            end_time=self.now,
            resource_id="kg1",
            actor_id="user1",
            pagination=PaginationParams(page=1, page_size=10)
        )

        # Only return the first log that matches all filters
        self.audit_repository.get_logs.return_value = ([self.sample_logs[0]], 1)

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert len(response.logs) == 1
        assert response.total_count == 1
        assert response.logs[0].id == "log1"
        
        # Check that repository was called with correct filter parameters
        self.audit_repository.get_logs.assert_called_once()
        call_args = self.audit_repository.get_logs.call_args[1]
        filter_criteria = call_args["filter_criteria"]
        assert filter_criteria.tenant_id == "tenant1"
        assert filter_criteria.resource_type == "knowledge_graph"
        assert filter_criteria.action == "create"
        assert filter_criteria.severity == AuditLogSeverity.INFO
        assert filter_criteria.category == AuditLogCategory.DATA_MODIFICATION
        assert filter_criteria.resource_id == "kg1"
        assert filter_criteria.user_id == "user1"  # actor_id maps to user_id in filter
        assert filter_criteria.start_time == request.start_time
        assert filter_criteria.end_time == request.end_time

    @pytest.mark.anyio
    async def test_get_audit_logs_with_summary(self):
        """Test audit logs retrieval with summary."""
        # Arrange
        request = GetAuditLogsRequest(
            user_id="admin1",
            tenant_id="tenant1",
            include_summary=True,
            pagination=PaginationParams(page=1, page_size=10)
        )

        self.audit_repository.get_logs.return_value = (self.sample_logs, 3)
        self.audit_repository.get_summary.return_value = self.sample_summary

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert len(response.logs) == 3
        assert response.summary is not None
        assert response.summary == self.sample_summary
        
        # Check that summary was requested
        self.audit_repository.get_summary.assert_called_once()
        call_args = self.audit_repository.get_summary.call_args[1]
        assert isinstance(call_args["filter_criteria"], AuditLogFilter)
        assert call_args["filter_criteria"].tenant_id == "tenant1"

    @pytest.mark.anyio
    async def test_get_audit_logs_default_pagination(self):
        """Test audit logs retrieval with default pagination."""
        # Arrange
        request = GetAuditLogsRequest(
            user_id="admin1",
            tenant_id="tenant1",
            # No pagination specified
        )

        self.audit_repository.get_logs.return_value = (self.sample_logs[:2], 3)  # First page

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert len(response.logs) == 2
        assert response.total_count == 3
        
        # Check that default pagination was applied
        self.audit_repository.get_logs.assert_called_once()
        call_args = self.audit_repository.get_logs.call_args[1]
        assert call_args["page"] == 1
        assert call_args["page_size"] == 20  # Default page size

    @pytest.mark.anyio
    async def test_get_audit_logs_invalid_severity(self):
        """Test error handling for invalid severity."""
        # Arrange
        request = GetAuditLogsRequest(
            user_id="admin1",
            tenant_id="tenant1",
            severity="invalid_severity"  # Invalid severity
        )

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Invalid severity" in response.error_message
        assert len(response.logs) == 0
        
        self.audit_repository.get_logs.assert_not_called()
        self.authorization_port.check_permission.assert_not_called()

    @pytest.mark.anyio
    async def test_get_audit_logs_invalid_category(self):
        """Test error handling for invalid category."""
        # Arrange
        request = GetAuditLogsRequest(
            user_id="admin1",
            tenant_id="tenant1",
            category="invalid_category"  # Invalid category
        )

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Invalid category" in response.error_message
        assert len(response.logs) == 0
        
        self.audit_repository.get_logs.assert_not_called()
        self.authorization_port.check_permission.assert_not_called()

    @pytest.mark.anyio
    async def test_get_audit_logs_invalid_time_range(self):
        """Test error handling for invalid time range."""
        # Arrange
        request = GetAuditLogsRequest(
            user_id="admin1",
            tenant_id="tenant1",
            start_time=self.now,
            end_time=self.now - timedelta(hours=1)  # End time before start time
        )

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Start time must be before end time" in response.error_message
        assert len(response.logs) == 0
        
        self.audit_repository.get_logs.assert_not_called()
        self.authorization_port.check_permission.assert_not_called()

    @pytest.mark.anyio
    async def test_get_audit_logs_authorization_error(self):
        """Test authorization error handling."""
        # Arrange
        request = GetAuditLogsRequest(
            user_id="regular_user",
            tenant_id="tenant1"
        )

        self.authorization_port.check_permission.side_effect = AuthorizationError(
            message="Permission denied",
            user_id="regular_user",
            resource_type="audit_logs",
            permission="view_audit_logs"
        )

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Permission denied" in response.error_message
        assert len(response.logs) == 0
        
        self.audit_repository.get_logs.assert_not_called()
        self.tracer.record_metric.assert_called_with(
            name="audit_logs_query_errors",
            value=1,
            error_type="AuthorizationError",
        )

    @pytest.mark.anyio
    async def test_get_audit_logs_repository_error(self):
        """Test repository error handling."""
        # Arrange
        request = GetAuditLogsRequest(
            user_id="admin1",
            tenant_id="tenant1"
        )

        self.audit_repository.get_logs.side_effect = Exception("Database connection error")

        # Act & Assert
        with pytest.raises(ApplicationError) as exc_info:
            await self.use_case.execute(request)
        
        assert "Failed to get audit logs" in str(exc_info.value)
        assert exc_info.value.error_code == "AUDIT_LOGS_QUERY_FAILED"
        self.tracer.record_metric.assert_called_with(
            name="audit_logs_query_errors",
            value=1,
            error_type="Exception",
        )