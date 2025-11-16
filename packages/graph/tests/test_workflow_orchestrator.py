"""Unit tests for WorkflowOrchestrator using mock ports and property-based testing.

This test suite uses both traditional unit tests with mocks and property-based
testing with hypothesis to thoroughly test the WorkflowOrchestrator service.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, call

import pytest

from application.ports import (
    GraphRetrieverPort,
    MessageBusPort,
    QueryTranslatorPort,
    TracingPort,
)
from domain.entities import Triple
from domain.services import GraphRAGException, WorkflowOrchestrator

pytest.importorskip("hypothesis")
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.extra.datetime import datetimes


class TestWorkflowOrchestrator:
    """Test suite for WorkflowOrchestrator domain service."""

    @pytest.fixture
    def mock_retriever(self) -> Mock:
        """Mock GraphRetrieverPort for testing."""
        mock = Mock(spec=GraphRetrieverPort)
        return mock

    @pytest.fixture
    def mock_translator(self) -> Mock:
        """Mock QueryTranslatorPort for testing."""
        mock = Mock(spec=QueryTranslatorPort)
        return mock

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
    def orchestrator(
        self,
        mock_retriever: Mock,
        mock_translator: Mock,
        mock_message_bus: Mock,
        mock_tracer: Mock,
    ) -> WorkflowOrchestrator:
        """WorkflowOrchestrator instance with mocked dependencies."""
        return WorkflowOrchestrator(
            retriever=mock_retriever,
            translator=mock_translator,
            message_bus=mock_message_bus,
            tracer=mock_tracer,
        )

    def test_register_workflow(
        self, orchestrator: WorkflowOrchestrator, mock_tracer: Mock
    ):
        """Test workflow registration with valid steps."""
        # Arrange
        workflow_id = "wf123"
        steps = [
            {
                "type": "graphrag_query",
                "name": "query_step",
                "question": "Who works at TechCorp?",
            },
            {"type": "graphrag_index", "name": "index_step", "docs": ["doc1", "doc2"]},
        ]
        framework = "flowise"
        tenant_id = "tenant1"

        # Act
        orchestrator.register_workflow(
            workflow_id=workflow_id,
            steps=steps,
            framework=framework,
            tenant_id=tenant_id,
        )

        # Assert
        assert workflow_id in orchestrator.registered_workflows
        workflow = orchestrator.registered_workflows[workflow_id]
        assert workflow["steps"] == steps
        assert workflow["framework"] == framework
        assert workflow["tenant_id"] == tenant_id
        assert workflow["status"] == "registered"
        assert "created_at" in workflow

        # Verify tracing
        mock_tracer.start_span.assert_called_once()

        # Verify bus event
        orchestrator.message_bus.publish.assert_called_with(
            topic="workflows.registered",
            message=pytest.ANY,
            tenant_id=tenant_id,
            idempotency_key=f"register_{workflow_id}",
        )

    def test_register_workflow_validation(self, orchestrator: WorkflowOrchestrator):
        """Test validation during workflow registration."""
        # Arrange
        workflow_id = "wf123"
        tenant_id = "tenant1"

        # Test with empty steps
        with pytest.raises(ValueError) as exc_info:
            orchestrator.register_workflow(
                workflow_id=workflow_id,
                steps=[],
                framework="flowise",
                tenant_id=tenant_id,
            )
        assert "at least one step" in str(exc_info.value)

        # Test with missing type
        with pytest.raises(ValueError) as exc_info:
            orchestrator.register_workflow(
                workflow_id=workflow_id,
                steps=[{"name": "step1"}],
                framework="flowise",
                tenant_id=tenant_id,
            )
        assert "missing required 'type'" in str(exc_info.value)

        # Test with invalid type
        with pytest.raises(ValueError) as exc_info:
            orchestrator.register_workflow(
                workflow_id=workflow_id,
                steps=[{"type": "invalid_type", "name": "step1"}],
                framework="flowise",
                tenant_id=tenant_id,
            )
        assert "invalid type" in str(exc_info.value)

        # Test with missing required fields
        with pytest.raises(ValueError) as exc_info:
            orchestrator.register_workflow(
                workflow_id=workflow_id,
                steps=[{"type": "graphrag_query", "name": "step1"}],  # Missing question
                framework="flowise",
                tenant_id=tenant_id,
            )
        assert "missing required 'question'" in str(exc_info.value)

    def test_execute_workflow_success(
        self,
        orchestrator: WorkflowOrchestrator,
        mock_retriever: Mock,
        mock_tracer: Mock,
    ):
        """Test successful workflow execution."""
        # Arrange
        workflow_id = "wf123"
        steps = [
            {
                "type": "graphrag_query",
                "name": "query_step",
                "question": "Who works at {company}?",
            }
        ]
        framework = "flowise"
        tenant_id = "tenant1"

        # Register workflow
        orchestrator.register_workflow(
            workflow_id=workflow_id,
            steps=steps,
            framework=framework,
            tenant_id=tenant_id,
        )

        # Setup mock retriever
        mock_retriever.run.return_value = "Alice works at TechCorp"

        # Act
        input_data = {"company": "TechCorp"}
        result = orchestrator.execute_workflow(
            workflow_id=workflow_id, input_data=input_data, tenant_id=tenant_id
        )

        # Assert
        assert result["status"] == "completed"
        assert "results" in result
        assert "step_0" in result["results"]
        assert result["results"]["step_0"]["status"] == "completed"

        # Verify retriever was called with template substitution
        mock_retriever.run.assert_called_once()
        call_args = mock_retriever.run.call_args
        assert call_args[1]["question"] == "Who works at TechCorp?"

        # Verify metrics
        mock_tracer.record_metric.assert_called()
        metric_calls = [
            call
            for call in mock_tracer.record_metric.call_args_list
            if call[1]["name"] == "workflow.execution_time_ms"
        ]
        assert len(metric_calls) == 1

        # Verify bus events for start and completion
        publish_topics = [c.kwargs["topic"] for c in orchestrator.message_bus.publish.call_args_list]
        assert "workflows.started" in publish_topics
        assert "workflows.completed" in publish_topics

    def test_span_closed(
        self,
        orchestrator: WorkflowOrchestrator,
        mock_retriever: Mock,
        mock_tracer: Mock,
    ):
        """Span should close after workflow execution."""
        workflow_id = "wf123"
        orchestrator.register_workflow(
            workflow_id=workflow_id,
            steps=[{"type": "graphrag_query", "question": "hi"}],
            framework="flowise",
            tenant_id="tenant1",
        )

        span = MagicMock()
        mock_tracer.start_span.return_value = span
        mock_retriever.run.return_value = "ok"

        orchestrator.execute_workflow(
            workflow_id=workflow_id, input_data={}, tenant_id="tenant1"
        )

        span.end.assert_called_once()

    def test_execute_workflow_step_failure_with_fallback(
        self, orchestrator: WorkflowOrchestrator, mock_retriever: Mock
    ):
        """Test workflow execution with step failure and fallback."""
        # Arrange
        workflow_id = "wf123"
        steps = [
            {
                "type": "graphrag_query",
                "name": "query_step",
                "question": "Who works at TechCorp?",
                "fallback": {
                    "type": "graphrag_query",
                    "question": "List employees at TechCorp",
                },
            }
        ]
        framework = "flowise"
        tenant_id = "tenant1"

        # Register workflow
        orchestrator.register_workflow(
            workflow_id=workflow_id,
            steps=steps,
            framework=framework,
            tenant_id=tenant_id,
        )

        # Setup mock retriever to fail on first call, succeed on second
        mock_retriever.run.side_effect = [
            Exception("Query failed"),
            "Bob and Alice work at TechCorp",
        ]

        # Act
        result = orchestrator.execute_workflow(
            workflow_id=workflow_id, input_data={}, tenant_id=tenant_id
        )

        # Assert
        assert result["status"] == "completed"  # Should complete with fallback
        assert "step_0" in result["results"]
        assert result["results"]["step_0"]["status"] == "failed"
        assert "step_0_fallback" in result["results"]
        assert result["results"]["step_0_fallback"]["status"] == "completed"

        # Verify both calls to retriever
        assert mock_retriever.run.call_count == 2
        first_call = mock_retriever.run.call_args_list[0]
        second_call = mock_retriever.run.call_args_list[1]
        assert first_call[1]["question"] == "Who works at TechCorp?"
        assert second_call[1]["question"] == "List employees at TechCorp"

    def test_execute_workflow_step_and_fallback_failure(
        self,
        orchestrator: WorkflowOrchestrator,
        mock_retriever: Mock,
        mock_tracer: Mock,
    ):
        """Test workflow execution with both step and fallback failure."""
        # Arrange
        workflow_id = "wf123"
        steps = [
            {
                "type": "graphrag_query",
                "name": "query_step",
                "question": "Who works at TechCorp?",
                "fallback": {
                    "type": "graphrag_query",
                    "question": "List employees at TechCorp",
                },
            }
        ]
        framework = "flowise"
        tenant_id = "tenant1"

        # Register workflow
        orchestrator.register_workflow(
            workflow_id=workflow_id,
            steps=steps,
            framework=framework,
            tenant_id=tenant_id,
        )

        # Setup mock retriever to fail on all calls
        mock_retriever.run.side_effect = Exception("Query failed")

        # Act
        result = orchestrator.execute_workflow(
            workflow_id=workflow_id, input_data={}, tenant_id=tenant_id
        )

        # Assert
        assert result["status"] == "failed"
        assert "error" in result
        assert "step_0" in result["results"]
        assert result["results"]["step_0"]["status"] == "failed"

        # Verify metrics for fallback failure
        mock_tracer.record_metric.assert_called()
        fallback_calls = [
            call
            for call in mock_tracer.record_metric.call_args_list
            if call[1]["name"] == "workflow.fallback_failures"
        ]
        assert len(fallback_calls) == 1

    def test_execute_workflow_not_found(self, orchestrator: WorkflowOrchestrator):
        """Test execution of non-existent workflow."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            orchestrator.execute_workflow(
                workflow_id="nonexistent", input_data={}, tenant_id="tenant1"
            )

        assert "Workflow not found" in str(exc_info.value)

    def test_execute_workflow_tenant_mismatch(self, orchestrator: WorkflowOrchestrator):
        """Test execution with tenant mismatch."""
        # Arrange
        workflow_id = "wf123"
        steps = [{"type": "graphrag_query", "name": "step1", "question": "test"}]

        # Register workflow for tenant1
        orchestrator.register_workflow(
            workflow_id=workflow_id,
            steps=steps,
            framework="flowise",
            tenant_id="tenant1",
        )

        # Act & Assert - Try to execute for tenant2
        with pytest.raises(ValueError) as exc_info:
            orchestrator.execute_workflow(
                workflow_id=workflow_id, input_data={}, tenant_id="tenant2"
            )

        assert "does not belong to tenant" in str(exc_info.value)

    def test_execute_condition_step(
        self, orchestrator: WorkflowOrchestrator, mock_retriever: Mock
    ):
        """Test execution of conditional workflow steps."""
        # Arrange
        workflow_id = "wf123"
        steps = [
            {
                "type": "condition",
                "name": "condition_step",
                "condition": "count > 0",
                "then": {"type": "graphrag_query", "question": "Show details"},
                "else": {"type": "graphrag_query", "question": "No results found"},
            }
        ]
        framework = "flowise"
        tenant_id = "tenant1"

        # Register workflow
        orchestrator.register_workflow(
            workflow_id=workflow_id,
            steps=steps,
            framework=framework,
            tenant_id=tenant_id,
        )

        # Setup mock retriever
        mock_retriever.run.return_value = "Details shown"

        # Act - Test true condition
        result_true = orchestrator.execute_workflow(
            workflow_id=workflow_id, input_data={"count": 5}, tenant_id=tenant_id
        )

        # Reset mock
        mock_retriever.reset_mock()
        mock_retriever.run.return_value = "No results message"

        # Act - Test false condition
        result_false = orchestrator.execute_workflow(
            workflow_id=workflow_id, input_data={"count": 0}, tenant_id=tenant_id
        )

        # Assert
        assert result_true["status"] == "completed"
        assert result_false["status"] == "completed"

        # Verify correct branch was taken each time
        true_call = mock_retriever.run.call_args_list[0]
        false_call = mock_retriever.run.call_args_list[1]
        assert true_call[1]["question"] == "Show details"
        assert false_call[1]["question"] == "No results found"

    def test_execute_graphrag_index_step(
        self, orchestrator: WorkflowOrchestrator, mock_retriever: Mock
    ):
        """Test execution of graphrag_index step."""
        # Arrange
        workflow_id = "wf123"
        steps = [
            {
                "type": "graphrag_index",
                "name": "index_step",
                "docs": ["doc1", "doc2"],
                "kg_id": "test_kg",
            }
        ]
        framework = "flowise"
        tenant_id = "tenant1"

        # Register workflow
        orchestrator.register_workflow(
            workflow_id=workflow_id,
            steps=steps,
            framework=framework,
            tenant_id=tenant_id,
        )

        # Setup mock retriever
        mock_retriever.index.return_value = [
            Triple("Entity1", "relates_to", "Entity2", tenant_id),
            Triple("Entity2", "type", "Person", tenant_id),
        ]

        # Act
        result = orchestrator.execute_workflow(
            workflow_id=workflow_id, input_data={}, tenant_id=tenant_id
        )

        # Assert
        assert result["status"] == "completed"
        assert "step_0" in result["results"]
        assert result["results"]["step_0"]["status"] == "completed"
        assert result["results"]["step_0"]["output"]["count"] == 2

        # Verify retriever was called correctly
        mock_retriever.index.assert_called_once_with(
            docs=["doc1", "doc2"], kg_id="test_kg", tenant_id=tenant_id
        )

    def test_execute_custom_function_step(self, orchestrator: WorkflowOrchestrator):
        """Test execution of custom_function step."""
        # Arrange
        workflow_id = "wf123"

        # Define custom function
        def custom_processor(data):
            return {
                "processed": True,
                "input": data,
                "timestamp": datetime.now().isoformat(),
            }

        steps = [
            {
                "type": "custom_function",
                "name": "custom_step",
                "function": "process",
                "process": custom_processor,
            }
        ]
        framework = "flowise"
        tenant_id = "tenant1"

        # Register workflow
        orchestrator.register_workflow(
            workflow_id=workflow_id,
            steps=steps,
            framework=framework,
            tenant_id=tenant_id,
        )

        # Act
        input_data = {"value": 42}
        result = orchestrator.execute_workflow(
            workflow_id=workflow_id, input_data=input_data, tenant_id=tenant_id
        )

        # Assert
        assert result["status"] == "completed"
        assert "step_0" in result["results"]
        assert result["results"]["step_0"]["status"] == "completed"
        output = result["results"]["step_0"]["output"]
        assert output["processed"] is True
        assert output["input"] == input_data

    def test_execute_custom_function_missing(self, orchestrator: WorkflowOrchestrator):
        """Test execution with missing custom function."""
        # Arrange
        workflow_id = "wf123"
        steps = [
            {
                "type": "custom_function",
                "name": "custom_step",
                "function": "missing_function",
            }
        ]
        framework = "flowise"
        tenant_id = "tenant1"

        # Register workflow
        orchestrator.register_workflow(
            workflow_id=workflow_id,
            steps=steps,
            framework=framework,
            tenant_id=tenant_id,
        )

        # Act
        result = orchestrator.execute_workflow(
            workflow_id=workflow_id, input_data={}, tenant_id=tenant_id
        )

        # Assert
        assert result["status"] == "failed"
        assert "step_0" in result["results"]
        assert result["results"]["step_0"]["status"] == "failed"
        assert "Custom function not found" in result["results"]["step_0"]["error"]

    def test_template_resolution(self, orchestrator: WorkflowOrchestrator):
        """Test template resolution in workflow steps."""
        # Test the private method directly
        template = "Hello {name}, your order {order_id} is {status}"
        data = {"name": "Alice", "order_id": "ORD-123", "status": "shipped"}

        result = orchestrator._resolve_template(template, data)
        assert result == "Hello Alice, your order ORD-123 is shipped"

        # Test with missing variables
        template = "Hello {name}, your order {order_id} is {missing}"
        result = orchestrator._resolve_template(template, data)
        assert result == "Hello Alice, your order ORD-123 is {missing}"

    def test_resolve_docs(self, orchestrator: WorkflowOrchestrator):
        """Test document resolution in workflow steps."""
        # Test with static docs
        static_docs = ["doc1", "doc2"]
        result = orchestrator._resolve_docs(static_docs, {})
        assert result == static_docs

        # Test with dynamic docs from input
        input_data = {"documents": ["doc3", "doc4"]}
        result = orchestrator._resolve_docs("{documents}", input_data)
        assert result == ["doc3", "doc4"]

    def test_evaluate_condition(self, orchestrator: WorkflowOrchestrator):
        """Test condition evaluation in workflow steps."""
        # Test simple conditions
        assert orchestrator._evaluate_condition("count > 0", {"count": 5}) is True
        assert orchestrator._evaluate_condition("count > 0", {"count": 0}) is False
        assert orchestrator._evaluate_condition("count == 0", {"count": 0}) is True

        # Test complex conditions
        assert (
            orchestrator._evaluate_condition(
                "count > 0 and status == 'active'", {"count": 5, "status": "active"}
            )
            is True
        )

        assert (
            orchestrator._evaluate_condition(
                "count > 0 and status == 'active'", {"count": 5, "status": "inactive"}
            )
            is False
        )

        # Malformed or unsafe expressions should fail gracefully
        assert (
            orchestrator._evaluate_condition("__import__('os').system('echo hi')", {})
            is False
        )

    def test_orchestrator_without_tracer(
        self, mock_retriever: Mock, mock_translator: Mock, mock_message_bus: Mock
    ):
        """Test orchestrator operation without tracing capabilities."""
        # Arrange
        orchestrator = WorkflowOrchestrator(
            retriever=mock_retriever,
            translator=mock_translator,
            message_bus=mock_message_bus,
            tracer=None,  # No tracer
        )

        workflow_id = "wf123"
        steps = [{"type": "graphrag_query", "name": "query_step", "question": "test"}]

        # Register workflow
        orchestrator.register_workflow(
            workflow_id=workflow_id,
            steps=steps,
            framework="flowise",
            tenant_id="tenant1",
        )

        # Setup mock
        mock_retriever.run.return_value = "Test result"

        # Act
        result = orchestrator.execute_workflow(
            workflow_id=workflow_id, input_data={}, tenant_id="tenant1"
        )

        # Assert
        assert result["status"] == "completed"
        # Should work fine without tracer

    @given(
        workflow_id=st.text(min_size=1),
        framework=st.text(min_size=1),
        tenant_id=st.text(min_size=1),
        question=st.text(min_size=1, max_size=100),
        input_key=st.text(min_size=1, max_size=10),
        input_value=st.text(min_size=1, max_size=20),
    )
    def test_property_based_workflow_execution(
        self,
        orchestrator: WorkflowOrchestrator,
        mock_retriever: Mock,
        workflow_id: str,
        framework: str,
        tenant_id: str,
        question: str,
        input_key: str,
        input_value: str,
    ):
        """Property-based test for workflow execution with various inputs."""
        # Arrange
        steps = [
            {
                "type": "graphrag_query",
                "name": "query_step",
                "question": f"Query: {{{input_key}}}",
            }
        ]

        # Register workflow
        orchestrator.register_workflow(
            workflow_id=workflow_id,
            steps=steps,
            framework=framework,
            tenant_id=tenant_id,
        )

        # Setup mock
        mock_retriever.run.return_value = "Test result"

        # Act
        input_data = {input_key: input_value}
        result = orchestrator.execute_workflow(
            workflow_id=workflow_id, input_data=input_data, tenant_id=tenant_id
        )

        # Assert
        assert result["status"] == "completed"
        assert "step_0" in result["results"]
        assert result["results"]["step_0"]["status"] == "completed"

        # Verify template substitution
        mock_retriever.run.assert_called_once()
        call_args = mock_retriever.run.call_args
        assert call_args[1]["question"] == f"Query: {input_value}"
        assert call_args[1]["tenant_id"] == tenant_id


if __name__ == "__main__":
    pytest.main(["-v", __file__])
