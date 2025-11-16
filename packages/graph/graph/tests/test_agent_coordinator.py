"""Unit tests for AgentCoordinator using mock ports."""

import pytest
from unittest.mock import Mock, MagicMock, call
from datetime import datetime
from typing import List, Dict, Any, Callable

from domain.entities import Triple, JobStatus
from domain.services import AgentCoordinator, CoordinationException
from application.ports.messaging import MessageBusPort
from application.ports import TracingPort


class TestAgentCoordinator:
    """Test suite for AgentCoordinator domain service."""

    @pytest.fixture
    def mock_message_bus(self) -> Mock:
        """Mock MessageBusPort for testing."""
        mock = Mock(spec=MessageBusPort)
        return mock

    @pytest.fixture
    def mock_tracer(self) -> Mock:
        """Mock TracingPort for testing."""
        mock = Mock(spec=TracingPort)
        mock.start_span.return_value = MagicMock()
        return mock

    @pytest.fixture
    def agent_coordinator(
        self, mock_message_bus: Mock, mock_tracer: Mock
    ) -> AgentCoordinator:
        """AgentCoordinator instance with mocked dependencies."""
        return AgentCoordinator(message_bus=mock_message_bus, tracer=mock_tracer)

    def test_coordinate_ingestion_workflow(
        self,
        agent_coordinator: AgentCoordinator,
        mock_message_bus: Mock,
        mock_tracer: Mock,
    ):
        """Test successful coordination of document ingestion workflow.

        Requirements tested:
        - 3.1: Multi-agent coordination
        - 3.2: Asynchronous workflow management
        - 8.1: Idempotent operations
        """
        # Arrange
        document_ids = ["doc1", "doc2", "doc3"]
        kg_id = "kg123"
        tenant_id = "tenant1"
        workflow_id = "wf123"
        ontology_version_id = "onto_v1"
        callback_topic = "workflows.ingestion.completed"

        # Act
        result = agent_coordinator.coordinate_ingestion_workflow(
            document_ids=document_ids,
            kg_id=kg_id,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            ontology_version_id=ontology_version_id,
            callback_topic=callback_topic,
        )

        # Assert
        assert result == workflow_id

        # Verify message bus interaction
        mock_message_bus.publish.assert_called_once()
        call_args = mock_message_bus.publish.call_args
        assert call_args[1]["topic"] == "workflows.ingestion.start"
        assert call_args[1]["tenant_id"] == tenant_id
        assert call_args[1]["idempotency_key"] == workflow_id

        # Verify message content
        message = call_args[1]["message"]
        assert message["workflow_id"] == workflow_id
        assert message["workflow_type"] == "document_ingestion"
        assert message["document_ids"] == document_ids
        assert message["kg_id"] == kg_id
        assert message["tenant_id"] == tenant_id
        assert message["ontology_version_id"] == ontology_version_id
        assert message["callback_topic"] == callback_topic
        assert message["status"] == JobStatus.PENDING
        assert len(message["steps"]) == 4  # Four workflow steps

        # Verify tracing
        mock_tracer.start_span.assert_called_once()
        mock_tracer.record_metric.assert_called_once()

    def test_coordinate_query_workflow(
        self,
        agent_coordinator: AgentCoordinator,
        mock_message_bus: Mock,
        mock_tracer: Mock,
    ):
        """Test successful coordination of query workflow.

        Requirements tested:
        - 3.1: Multi-agent coordination
        - 3.2: Asynchronous workflow management
        """
        # Arrange
        question = "Who works at TechCorp?"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"
        workflow_id = "wf456"
        callback_topic = "workflows.query.completed"
        query_opts = {"max_hops": 3, "return_triples": True}

        # Act
        result = agent_coordinator.coordinate_query_workflow(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id,
            user_id=user_id,
            workflow_id=workflow_id,
            callback_topic=callback_topic,
            query_opts=query_opts,
        )

        # Assert
        assert result == workflow_id

        # Verify message bus interaction
        mock_message_bus.publish.assert_called_once()
        call_args = mock_message_bus.publish.call_args
        assert call_args[1]["topic"] == "workflows.query.start"
        assert call_args[1]["tenant_id"] == tenant_id
        assert call_args[1]["idempotency_key"] == workflow_id

        # Verify message content
        message = call_args[1]["message"]
        assert message["workflow_id"] == workflow_id
        assert message["workflow_type"] == "natural_language_query"
        assert message["question"] == question
        assert message["kg_id"] == kg_id
        assert message["tenant_id"] == tenant_id
        assert message["user_id"] == user_id
        assert message["callback_topic"] == callback_topic
        assert message["query_opts"] == query_opts
        assert message["status"] == JobStatus.PENDING
        assert len(message["steps"]) == 3  # Three workflow steps

        # Verify tracing
        mock_tracer.start_span.assert_called_once()
        mock_tracer.record_metric.assert_called_once()

    def test_register_workflow_handler(
        self, agent_coordinator: AgentCoordinator, mock_message_bus: Mock
    ):
        """Test registration of workflow message handlers."""
        # Arrange
        topic = "workflows.status.updates"
        tenant_id = "tenant1"
        handler = lambda msg: None

        # Act
        agent_coordinator.register_workflow_handler(
            topic=topic, handler=handler, tenant_id=tenant_id
        )

        # Assert
        mock_message_bus.subscribe.assert_called_once_with(
            topic=topic, handler=handler, tenant_id=tenant_id
        )

        # Verify handler is stored
        handler_key = f"{topic}:{tenant_id}"
        assert handler_key in agent_coordinator.registered_handlers
        assert agent_coordinator.registered_handlers[handler_key] == handler

    def test_update_workflow_status(
        self,
        agent_coordinator: AgentCoordinator,
        mock_message_bus: Mock,
        mock_tracer: Mock,
    ):
        """Test workflow status updates with progress tracking."""
        # Arrange
        workflow_id = "wf123"
        step_name = "entity_extraction"
        status = JobStatus.COMPLETED
        tenant_id = "tenant1"
        result = {"extracted_triples": 42}

        # Act
        agent_coordinator.update_workflow_status(
            workflow_id=workflow_id,
            step_name=step_name,
            status=status,
            tenant_id=tenant_id,
            result=result,
        )

        # Assert
        # Should publish to two topics
        assert mock_message_bus.publish.call_count == 2

        # Check first call - workflow specific topic
        first_call = mock_message_bus.publish.call_args_list[0]
        assert first_call[1]["topic"] == f"workflows.status.{workflow_id}"
        assert first_call[1]["tenant_id"] == tenant_id

        # Check second call - general status topic
        second_call = mock_message_bus.publish.call_args_list[1]
        assert second_call[1]["topic"] == "workflows.status.updates"
        assert second_call[1]["tenant_id"] == tenant_id

        # Verify message content (both messages should be identical)
        for call_args in mock_message_bus.publish.call_args_list:
            message = call_args[1]["message"]
            assert message["workflow_id"] == workflow_id
            assert message["step_name"] == step_name
            assert message["status"] == status
            assert message["tenant_id"] == tenant_id
            assert message["result"] == result
            assert "updated_at" in message

        # Verify metric recording for completed step
        mock_tracer.record_metric.assert_called_once()
        metric_call = mock_tracer.record_metric.call_args
        assert metric_call[1]["name"] == "coordinator.workflow_steps_completed"
        assert metric_call[1]["tenant_id"] == tenant_id
        assert metric_call[1]["step_name"] == step_name

    def test_update_workflow_status_invalid_status(
        self, agent_coordinator: AgentCoordinator
    ):
        """Test validation of workflow status values."""
        # Arrange
        workflow_id = "wf123"
        step_name = "entity_extraction"
        invalid_status = "unknown_status"  # Not in valid statuses
        tenant_id = "tenant1"

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            agent_coordinator.update_workflow_status(
                workflow_id=workflow_id,
                step_name=step_name,
                status=invalid_status,
                tenant_id=tenant_id,
            )

        assert "Invalid status" in str(exc_info.value)

    def test_ingestion_workflow_failure(
        self,
        agent_coordinator: AgentCoordinator,
        mock_message_bus: Mock,
        mock_tracer: Mock,
    ):
        """Test handling of ingestion workflow coordination failures."""
        # Arrange
        document_ids = ["doc1", "doc2"]
        kg_id = "kg123"
        tenant_id = "tenant1"
        workflow_id = "wf123"
        ontology_version_id = "onto_v1"

        # Mock message bus to raise exception
        mock_message_bus.publish.side_effect = Exception("Message bus unavailable")

        # Act & Assert
        with pytest.raises(CoordinationException) as exc_info:
            agent_coordinator.coordinate_ingestion_workflow(
                document_ids=document_ids,
                kg_id=kg_id,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                ontology_version_id=ontology_version_id,
            )

        assert exc_info.value.error_code == "COORDINATION_FAILED"
        assert "Failed to coordinate ingestion workflow" in exc_info.value.message
        assert exc_info.value.context["workflow_id"] == workflow_id
        assert exc_info.value.context["kg_id"] == kg_id
        assert exc_info.value.context["tenant_id"] == tenant_id

        # Verify error metric was recorded
        mock_tracer.record_metric.assert_called_once()
        metric_call = mock_tracer.record_metric.call_args
        assert metric_call[1]["name"] == "coordinator.workflow_errors"
        assert metric_call[1]["tenant_id"] == tenant_id

    def test_query_workflow_failure(
        self,
        agent_coordinator: AgentCoordinator,
        mock_message_bus: Mock,
        mock_tracer: Mock,
    ):
        """Test handling of query workflow coordination failures."""
        # Arrange
        question = "Who works at TechCorp?"
        kg_id = "kg123"
        tenant_id = "tenant1"
        user_id = "user1"
        workflow_id = "wf456"

        # Mock message bus to raise exception
        mock_message_bus.publish.side_effect = Exception("Message bus unavailable")

        # Act & Assert
        with pytest.raises(CoordinationException) as exc_info:
            agent_coordinator.coordinate_query_workflow(
                question=question,
                kg_id=kg_id,
                tenant_id=tenant_id,
                user_id=user_id,
                workflow_id=workflow_id,
            )

        assert exc_info.value.error_code == "COORDINATION_FAILED"
        assert "Failed to coordinate query workflow" in exc_info.value.message
        assert exc_info.value.context["workflow_id"] == workflow_id
        assert exc_info.value.context["kg_id"] == kg_id
        assert exc_info.value.context["tenant_id"] == tenant_id
        assert exc_info.value.context["user_id"] == user_id

    def test_handler_registration_failure(
        self, agent_coordinator: AgentCoordinator, mock_message_bus: Mock
    ):
        """Test handling of handler registration failures."""
        # Arrange
        topic = "workflows.status.updates"
        tenant_id = "tenant1"
        handler = lambda msg: None

        # Mock message bus to raise exception
        mock_message_bus.subscribe.side_effect = Exception("Subscription failed")

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            agent_coordinator.register_workflow_handler(
                topic=topic, handler=handler, tenant_id=tenant_id
            )

        assert "Failed to register workflow handler" in str(exc_info.value)

        # Handler should not be stored on failure
        handler_key = f"{topic}:{tenant_id}"
        assert handler_key not in agent_coordinator.registered_handlers

    def test_status_update_failure(
        self,
        agent_coordinator: AgentCoordinator,
        mock_message_bus: Mock,
        mock_tracer: Mock,
    ):
        """Test handling of status update failures."""
        # Arrange
        workflow_id = "wf123"
        step_name = "entity_extraction"
        status = JobStatus.COMPLETED
        tenant_id = "tenant1"

        # Mock message bus to raise exception
        mock_message_bus.publish.side_effect = Exception("Message bus unavailable")

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            agent_coordinator.update_workflow_status(
                workflow_id=workflow_id,
                step_name=step_name,
                status=status,
                tenant_id=tenant_id,
            )

        assert "Failed to update workflow status" in str(exc_info.value)

        # Verify error metric was recorded
        mock_tracer.record_metric.assert_called_once()
        metric_call = mock_tracer.record_metric.call_args
        assert metric_call[1]["name"] == "coordinator.status_update_errors"
        assert metric_call[1]["tenant_id"] == tenant_id

    def test_coordinator_without_tracer(self, mock_message_bus: Mock):
        """Test coordinator operation without tracing capabilities."""
        # Arrange
        coordinator = AgentCoordinator(
            message_bus=mock_message_bus, tracer=None  # No tracer
        )

        document_ids = ["doc1", "doc2"]
        kg_id = "kg123"
        tenant_id = "tenant1"
        workflow_id = "wf123"
        ontology_version_id = "onto_v1"

        # Act
        result = coordinator.coordinate_ingestion_workflow(
            document_ids=document_ids,
            kg_id=kg_id,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            ontology_version_id=ontology_version_id,
        )

        # Assert
        assert result == workflow_id
        mock_message_bus.publish.assert_called_once()
        # Should work fine without tracer


if __name__ == "__main__":
    pytest.main([__file__])
