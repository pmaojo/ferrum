"""Unit tests for AutoGen Studio integration."""

import pytest
from unittest.mock import Mock, MagicMock, call
import uuid
from typing import Dict, Any, List
from datetime import datetime

from domain.entities import Triple
from application.ports import GraphRetrieverPort, MessageBusPort, TracingPort
from adapters.inmemory_message_bus_adapter import InMemoryMessageBusAdapter
from ui_adapters.autogen.graphrag_tool import (
    GraphRAGToolRegistry, tool, create_ask_graphrag_tool, register_with_autogen
)


class TestAutoGenIntegration:
    """Test suite for AutoGen Studio integration."""

    @pytest.fixture
    def mock_retriever(self) -> Mock:
        """Mock GraphRetrieverPort for testing."""
        mock = Mock(spec=GraphRetrieverPort)

        # Mock run method to return a sample response
        mock.run.return_value = "Sample GraphRAG response"

        # Mock index method to return sample triples
        mock.index.return_value = [
            Triple(subject="Entity1", predicate="relatesTo", object="Entity2", tenant_id="tenant1"),
            Triple(subject="Entity2", predicate="hasProperty", object="Value1", tenant_id="tenant1")
        ]

        return mock

    @pytest.fixture
    def mock_message_bus(self) -> Mock:
        """Mock MessageBusPort for testing."""
        mock = Mock(spec=MessageBusPort)
        return mock

    @pytest.fixture
    def memory_message_bus(self) -> InMemoryMessageBusAdapter:
        """Concrete message bus for integration-style tests."""
        return InMemoryMessageBusAdapter()

    @pytest.fixture
    def mock_tracer(self) -> Mock:
        """Mock TracingPort for testing."""
        mock = Mock(spec=TracingPort)
        mock.start_span.return_value = MagicMock()
        return mock

    @pytest.fixture
    def tool_registry(
        self,
        mock_retriever: Mock,
        mock_message_bus: Mock,
        mock_tracer: Mock
    ) -> GraphRAGToolRegistry:
        """GraphRAGToolRegistry instance with mocked dependencies."""
        return GraphRAGToolRegistry(
            retriever=mock_retriever,
            message_bus=mock_message_bus,
            tracer=mock_tracer
        )

    @pytest.fixture
    def memory_registry(
        self,
        mock_retriever: Mock,
        memory_message_bus: InMemoryMessageBusAdapter,
        mock_tracer: Mock,
    ) -> GraphRAGToolRegistry:
        """Registry using the in-memory message bus."""
        return GraphRAGToolRegistry(
            retriever=mock_retriever,
            message_bus=memory_message_bus,
            tracer=mock_tracer,
        )

    def test_tool_decorator(self):
        """Test the @tool decorator functionality."""
        # Define a test function
        @tool
        def test_function(arg1, arg2):
            """Test function docstring."""
            return arg1 + arg2

        # Check that decorator adds the expected attributes
        assert hasattr(test_function, "_tool")
        assert test_function._tool is True
        assert test_function._tool_name == "test_function"
        assert test_function._tool_description == "Test function docstring."

        # Check that the function still works as expected
        assert test_function(1, 2) == 3

    def test_registry_initialization(
        self,
        tool_registry: GraphRAGToolRegistry,
        mock_message_bus: Mock
    ):
        """Test initialization of GraphRAGToolRegistry."""
        # Verify message handlers are set up
        assert mock_message_bus.subscribe.call_count == 2

        # Check first subscription (query response)
        first_call = mock_message_bus.subscribe.call_args_list[0]
        assert first_call[1]["topic"] == "agents.graphrag.query.response"
        assert first_call[1]["tenant_id"] == "*"

        # Check second subscription (index response)
        second_call = mock_message_bus.subscribe.call_args_list[1]
        assert second_call[1]["topic"] == "agents.graphrag.index.response"
        assert second_call[1]["tenant_id"] == "*"

    def test_agent_registration(
        self,
        tool_registry: GraphRAGToolRegistry,
        mock_message_bus: Mock,
        mock_tracer: Mock
    ):
        """Test agent registration functionality."""
        # Arrange
        agent_id = "test_agent"
        tenant_id = "tenant1"
        capabilities = ["query"]

        # Act
        tool_registry.register_agent(
            agent_id=agent_id,
            tenant_id=tenant_id,
            capabilities=capabilities
        )

        # Assert
        # Verify agent is registered
        assert agent_id in tool_registry.registered_agents
        assert tool_registry.registered_agents[agent_id]["tenant_id"] == tenant_id
        assert tool_registry.registered_agents[agent_id]["capabilities"] == capabilities
        assert isinstance(
            tool_registry.registered_agents[agent_id]["registered_at"], datetime
        )

        # Verify subscription to agent-specific topic
        # Check that subscribe was called with the correct topic and tenant_id
        # We can't directly compare the lambda function
        call_args = mock_message_bus.subscribe.call_args_list[-1][1]
        assert call_args["topic"] == f"agents.{agent_id}.request"
        assert call_args["tenant_id"] == tenant_id
        assert callable(call_args["handler"])

        # Verify tracing
        mock_tracer.start_span.assert_called_with(
            name="graphrag_tool.register_agent",
            tenant_id=tenant_id,
            agent_id=agent_id,
            capabilities=capabilities
        )

    def test_create_ask_graphrag_tool(
        self,
        memory_registry: GraphRAGToolRegistry,
        mock_retriever: Mock
    ):
        """Test creation of bound ask_graphrag tool function."""
        # Create bound tool function
        bound_tool = create_ask_graphrag_tool(memory_registry)

        # Verify tool attributes
        assert hasattr(bound_tool, "_tool")
        assert bound_tool._tool is True
        assert bound_tool._tool_name == "bound_ask_graphrag"

        # Test tool execution
        question = "What is GraphRAG?"
        kg_id = "test_kg"
        tenant_id = "tenant1"

        # Execute tool
        result = bound_tool(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id
        )

        # Verify retriever was called
        mock_retriever.run.assert_called_with(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id,
            opts={}
        )

        # Verify result
        assert result == "Sample GraphRAG response"

    def test_register_with_autogen(self, tool_registry: GraphRAGToolRegistry):
        """Test registration with AutoGen Studio."""
        # Register tools
        tools = register_with_autogen(tool_registry)

        # Verify returned tools
        assert "ask_graphrag" in tools
        assert callable(tools["ask_graphrag"])
        assert hasattr(tools["ask_graphrag"], "_tool")
        assert tools["ask_graphrag"]._tool is True

    def test_handle_query_response(
        self,
        tool_registry: GraphRAGToolRegistry,
        mock_message_bus: Mock,
        mock_tracer: Mock
    ):
        """Test handling of query response messages."""
        # Arrange
        query_id = "test_query_id"
        agent_id = "test_agent"
        tenant_id = "tenant1"

        message = {
            "query_id": query_id,
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "status": "completed",
            "result": "Sample result",
            "question": "Test question"
        }

        # Act
        tool_registry._handle_query_response(message)

        # Assert
        # Verify message bus publish
        mock_message_bus.publish.assert_called_with(
            topic=f"agents.{agent_id}.response",
            message=message,
            tenant_id=tenant_id,
            idempotency_key=f"response_{query_id}"
        )

        # Verify tracing
        mock_tracer.start_span.assert_called_with(
            name="graphrag_tool.handle_query_response",
            tenant_id=tenant_id,
            query_id=query_id,
            agent_id=agent_id
        )

    def test_handle_index_response(
        self,
        tool_registry: GraphRAGToolRegistry,
        mock_message_bus: Mock,
        mock_tracer: Mock
    ):
        """Test handling of index response messages."""
        # Arrange
        index_id = "test_index_id"
        agent_id = "test_agent"
        tenant_id = "tenant1"

        message = {
            "index_id": index_id,
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "status": "completed",
            "triples": [{"subject": "Entity1", "predicate": "relatesTo", "object": "Entity2"}],
            "triple_count": 1
        }

        # Act
        tool_registry._handle_index_response(message)

        # Assert
        # Verify message bus publish
        mock_message_bus.publish.assert_called_with(
            topic=f"agents.{agent_id}.response",
            message=message,
            tenant_id=tenant_id,
            idempotency_key=f"response_{index_id}"
        )

        # Verify tracing
        mock_tracer.start_span.assert_called_with(
            name="graphrag_tool.handle_index_response",
            tenant_id=tenant_id,
            index_id=index_id,
            agent_id=agent_id
        )

    def test_process_query_request(
        self,
        tool_registry: GraphRAGToolRegistry,
        mock_retriever: Mock,
        mock_message_bus: Mock
    ):
        """Test processing of query requests."""
        # Arrange
        agent_id = "test_agent"
        query_id = "test_query_id"
        tenant_id = "tenant1"
        question = "What is GraphRAG?"
        kg_id = "test_kg"

        message = {
            "request_type": "query",
            "query_id": query_id,
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "question": question,
            "kg_id": kg_id,
            "opts": {"max_hops": 2}
        }

        # Act
        tool_registry._process_query_request(message, agent_id)

        # Assert
        # Verify retriever call
        mock_retriever.run.assert_called_with(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id,
            opts={"max_hops": 2}
        )

        # Verify message bus publish
        mock_message_bus.publish.assert_called_with(
            topic=f"agents.{agent_id}.response",
            message={
                "query_id": query_id,
                "agent_id": agent_id,
                "tenant_id": tenant_id,
                "status": "completed",
                "result": "Sample GraphRAG response",
                "question": question
            },
            tenant_id=tenant_id,
            idempotency_key=f"response_{query_id}"
        )

    def test_process_index_request(
        self,
        tool_registry: GraphRAGToolRegistry,
        mock_retriever: Mock,
        mock_message_bus: Mock
    ):
        """Test processing of index requests."""
        # Arrange
        agent_id = "test_agent"
        index_id = "test_index_id"
        tenant_id = "tenant1"
        docs = ["Document 1", "Document 2"]
        kg_id = "test_kg"

        message = {
            "request_type": "index",
            "index_id": index_id,
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "docs": docs,
            "kg_id": kg_id
        }

        # Act
        tool_registry._process_index_request(message, agent_id)

        # Assert
        # Verify retriever call
        mock_retriever.index.assert_called_with(
            docs=docs,
            kg_id=kg_id,
            tenant_id=tenant_id
        )

        # Verify message bus publish
        mock_message_bus.publish.assert_called_with(
            topic=f"agents.{agent_id}.response",
            message={
                "index_id": index_id,
                "agent_id": agent_id,
                "tenant_id": tenant_id,
                "status": "completed",
                "triples": [
                    {"subject": "Entity1", "predicate": "relatesTo", "object": "Entity2"},
                    {"subject": "Entity2", "predicate": "hasProperty", "object": "Value1"}
                ],
                "triple_count": 2
            },
            tenant_id=tenant_id,
            idempotency_key=f"response_{index_id}"
        )

    def test_process_query_request_error(
        self,
        tool_registry: GraphRAGToolRegistry,
        mock_retriever: Mock,
        mock_message_bus: Mock
    ):
        """Test error handling in query request processing."""
        # Arrange
        agent_id = "test_agent"
        query_id = "test_query_id"
        tenant_id = "tenant1"
        question = "What is GraphRAG?"
        kg_id = "test_kg"

        message = {
            "request_type": "query",
            "query_id": query_id,
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "question": question,
            "kg_id": kg_id
        }

        # Mock retriever to raise exception
        mock_retriever.run.side_effect = ValueError("Test error")

        # Act
        tool_registry._process_query_request(message, agent_id)

        # Assert
        # Verify error response
        mock_message_bus.publish.assert_called_with(
            topic=f"agents.{agent_id}.response",
            message={
                "query_id": query_id,
                "agent_id": agent_id,
                "tenant_id": tenant_id,
                "status": "failed",
                "error": "Test error",
                "question": question
            },
            tenant_id=tenant_id,
            idempotency_key=f"response_{query_id}"
        )

    def test_bound_tool_error_handling(
        self,
        memory_registry: GraphRAGToolRegistry,
        mock_retriever: Mock
    ):
        """Test error handling in bound tool function."""
        # Create bound tool function
        bound_tool = create_ask_graphrag_tool(memory_registry)

        # Mock retriever to raise exception
        mock_retriever.run.side_effect = ValueError("Test error")

        # Execute tool and verify exception
        with pytest.raises(ValueError) as exc_info:
            bound_tool(
                question="What is GraphRAG?",
                kg_id="test_kg",
                tenant_id="tenant1"
            )

        assert "GraphRAG query failed: Test error" in str(exc_info.value)

    def test_bound_tool_timeout(
        self,
        memory_registry: GraphRAGToolRegistry,
        monkeypatch
    ):
        """Tool raises TimeoutError when no agent response arrives."""
        bound_tool = create_ask_graphrag_tool(memory_registry)

        # Prevent response publication
        monkeypatch.setattr(memory_registry, "_process_query_request", lambda *a, **k: None)

        with pytest.raises(TimeoutError):
            bound_tool(
                question="What is GraphRAG?",
                kg_id="test_kg",
                tenant_id="tenant1",
                opts={"timeout": 0.1},
            )


if __name__ == "__main__":
    pytest.main([__file__])