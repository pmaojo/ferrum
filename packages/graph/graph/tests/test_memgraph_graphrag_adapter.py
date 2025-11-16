"""Tests for Memgraph GraphRAG adapter implementation."""

import pytest
pytest.importorskip("memgraph")
from unittest.mock import MagicMock, patch
from datetime import datetime

from domain.entities import Triple
from domain.services import GraphRAGException
from adapters.retrievers.memgraph_graphrag_adapter import MemgraphGraphRAGAdapter


@pytest.fixture
def mock_memgraph_client():
    """Create a mock Memgraph client."""
    return MagicMock()


@pytest.fixture
def mock_agentic_engine():
    """Create a mock AgenticGraphRagEngine."""
    return MagicMock()


@pytest.fixture
def mock_message_bus():
    """Create a mock MessageBusPort."""
    return MagicMock()


@pytest.fixture
def memgraph_adapter(mock_memgraph_client, mock_agentic_engine):
    """Create a MemgraphGraphRAGAdapter with mocked dependencies."""
    with patch("memgraph.agentic.MemgraphClient", return_value=mock_memgraph_client), \
         patch("memgraph.agentic.AgenticGraphRagEngine", return_value=mock_agentic_engine):
        adapter = MemgraphGraphRAGAdapter(
            memgraph_connection_string="bolt://localhost:7687",
            config={"engine": {"temperature": 0.5}}
        )
        return adapter


def test_initialization_with_valid_connection():
    """Test adapter initialization with valid connection string."""
    with patch("memgraph.agentic.MemgraphClient") as mock_client_cls, \
         patch("memgraph.agentic.AgenticGraphRagEngine") as mock_engine_cls:

        # Setup mocks
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_engine = MagicMock()
        mock_engine_cls.return_value = mock_engine

        # Initialize adapter
        adapter = MemgraphGraphRAGAdapter(
            memgraph_connection_string="bolt://localhost:7687"
        )

        # Verify initialization
        mock_client_cls.assert_called_once_with("bolt://localhost:7687")
        mock_engine_cls.assert_called_once()
        assert adapter.client == mock_client
        assert adapter.engine == mock_engine


def test_initialization_with_import_error():
    """Test adapter initialization when Memgraph libraries are not available."""
    with patch("memgraph.agentic.MemgraphClient", side_effect=ImportError("No module named 'memgraph'")):
        with pytest.raises(GraphRAGException) as excinfo:
            MemgraphGraphRAGAdapter(memgraph_connection_string="bolt://localhost:7687")

        assert "Memgraph libraries not installed" in str(excinfo.value)
        assert excinfo.value.error_code == "MEMGRAPH_IMPORT_ERROR"


def test_initialization_with_connection_error():
    """Test adapter initialization when connection fails."""
    with patch("memgraph.agentic.MemgraphClient", side_effect=Exception("Connection refused")):
        with pytest.raises(GraphRAGException) as excinfo:
            MemgraphGraphRAGAdapter(memgraph_connection_string="bolt://localhost:7687")

        assert "Failed to initialize Memgraph connection" in str(excinfo.value)
        assert excinfo.value.error_code == "MEMGRAPH_CONNECTION_ERROR"


def test_index_documents(memgraph_adapter, mock_agentic_engine):
    """Test indexing documents with Memgraph adapter."""
    # Setup mock response
    mock_agentic_engine.index_documents.return_value = {
        "triples": [
            {"subject": "Entity1", "predicate": "relatedTo", "object": "Entity2"},
            {"subject": "Entity2", "predicate": "hasProperty", "object": "Value1"}
        ],
        "status": "success",
        "document_count": 2
    }

    # Call index method
    docs = ["Document 1 content", "Document 2 content"]
    result = memgraph_adapter.index(
        docs=docs,
        kg_id="test-kg",
        tenant_id="tenant-1"
    )

    # Verify results
    assert len(result) == 2
    assert isinstance(result[0], Triple)
    assert result[0].subject == "Entity1"
    assert result[0].predicate == "relatedTo"
    assert result[0].object == "Entity2"
    assert result[0].tenant_id == "tenant-1"

    # Verify mock calls
    mock_agentic_engine.index_documents.assert_called_once()
    call_args = mock_agentic_engine.index_documents.call_args[1]
    assert call_args["kg_id"] == "test-kg"
    assert call_args["tenant_filter"] == "tenant-1"
    assert len(call_args["documents"]) == 2
    assert call_args["documents"][0]["content"] == "Document 1 content"
    assert call_args["documents"][0]["metadata"]["kg_id"] == "test-kg"
    assert call_args["documents"][0]["metadata"]["tenant_id"] == "tenant-1"


def test_index_documents_error(memgraph_adapter, mock_agentic_engine):
    """Test error handling during document indexing."""
    # Setup mock to raise exception
    mock_agentic_engine.index_documents.side_effect = Exception("Indexing failed")

    # Call index method and expect exception
    with pytest.raises(GraphRAGException) as excinfo:
        memgraph_adapter.index(
            docs=["Document content"],
            kg_id="test-kg",
            tenant_id="tenant-1"
        )

    # Verify exception details
    assert "Memgraph indexing failed" in str(excinfo.value)
    assert excinfo.value.error_code == "MEMGRAPH_INDEX_ERROR"
    assert excinfo.value.context["kg_id"] == "test-kg"
    assert excinfo.value.context["tenant_id"] == "tenant-1"


def test_run_query_text_response(memgraph_adapter, mock_agentic_engine):
    """Test running a query with text response."""
    # Setup mock response
    mock_agentic_engine.query.return_value = {
        "response": "This is the answer",
        "reasoning": "This is how I found the answer",
        "triples": [
            {"subject": "Entity1", "predicate": "relatedTo", "object": "Entity2"}
        ]
    }

    # Call run method
    result = memgraph_adapter.run(
        question="What is related to Entity1?",
        kg_id="test-kg",
        tenant_id="tenant-1"
    )

    # Verify results
    assert isinstance(result, str)
    assert "This is the answer" in result
    assert "Reasoning:" in result
    assert "This is how I found the answer" in result

    # Verify mock calls
    mock_agentic_engine.query.assert_called_once()
    call_args = mock_agentic_engine.query.call_args[1]
    assert call_args["question"] == "What is related to Entity1?"
    assert call_args["kg_id"] == "test-kg"
    assert call_args["tenant_id"] == "tenant-1"
    assert call_args["max_hops"] == 2
    assert call_args["context_tokens"] == 4096
    assert call_args["include_reasoning"] is True


def test_run_query_triples_response(memgraph_adapter, mock_agentic_engine):
    """Test running a query with triples response."""
    # Setup mock response
    mock_agentic_engine.query.return_value = {
        "response": "This is the answer",
        "triples": [
            {"subject": "Entity1", "predicate": "relatedTo", "object": "Entity2"},
            {"subject": "Entity2", "predicate": "hasProperty", "object": "Value1"}
        ]
    }

    # Call run method with return_triples=True
    result = memgraph_adapter.run(
        question="What is related to Entity1?",
        kg_id="test-kg",
        tenant_id="tenant-1",
        opts={"return_triples": True}
    )

    # Verify results
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], Triple)
    assert result[0].subject == "Entity1"
    assert result[0].predicate == "relatedTo"
    assert result[0].object == "Entity2"
    assert result[0].tenant_id == "tenant-1"


def test_run_query_with_custom_options(memgraph_adapter, mock_agentic_engine):
    """Test running a query with custom options."""
    # Setup mock response
    mock_agentic_engine.query.return_value = {
        "response": "This is the answer"
    }

    # Call run method with custom options
    memgraph_adapter.run(
        question="What is related to Entity1?",
        kg_id="test-kg",
        tenant_id="tenant-1",
        opts={
            "max_hops": 3,
            "context_tokens": 8192,
            "include_reasoning": False
        }
    )

    # Verify mock calls with custom options
    call_args = mock_agentic_engine.query.call_args[1]
    assert call_args["max_hops"] == 3
    assert call_args["context_tokens"] == 8192
    assert call_args["include_reasoning"] is False


def test_run_query_error(memgraph_adapter, mock_agentic_engine):
    """Test error handling during query execution."""
    # Setup mock to raise exception
    mock_agentic_engine.query.side_effect = Exception("Query failed")

    # Call run method and expect exception
    with pytest.raises(GraphRAGException) as excinfo:
        memgraph_adapter.run(
            question="What is related to Entity1?",
            kg_id="test-kg",
            tenant_id="tenant-1"
        )

    # Verify exception details
    assert "Memgraph query failed" in str(excinfo.value)
    assert excinfo.value.error_code == "MEMGRAPH_QUERY_ERROR"
    assert excinfo.value.context["kg_id"] == "test-kg"
    assert excinfo.value.context["tenant_id"] == "tenant-1"


def test_agent_mode_query(memgraph_adapter, mock_agentic_engine, mock_message_bus):
    """Test running a query in agent mode with message bus."""
    # Setup adapter with message bus
    memgraph_adapter.message_bus = mock_message_bus

    # Setup mock response
    mock_agentic_engine.query.return_value = {
        "response": "This is the agent-coordinated answer"
    }

    # Call run method with agent_mode=True
    result = memgraph_adapter.run(
        question="Complex question requiring multiple agents?",
        kg_id="test-kg",
        tenant_id="tenant-1",
        opts={"agent_mode": True}
    )

    # Verify results
    assert "This is the agent-coordinated answer" in result

    # Verify message bus publish calls
    assert mock_message_bus.publish.call_count == 2

    # Verify first publish call (query)
    first_call = mock_message_bus.publish.call_args_list[0][1]
    assert first_call["topic"] == "agent.coordination.query"
    assert first_call["message"]["question"] == "Complex question requiring multiple agents?"
    assert first_call["message"]["kg_id"] == "test-kg"
    assert first_call["tenant_id"] == "tenant-1"

    # Verify second publish call (result)
    second_call = mock_message_bus.publish.call_args_list[1][1]
    assert second_call["topic"] == "agent.coordination.result"
    assert second_call["message"]["result"]["response"] == "This is the agent-coordinated answer"
    assert second_call["tenant_id"] == "tenant-1"

    # Verify engine query call with agent coordination
    call_args = mock_agentic_engine.query.call_args[1]
    assert call_args["agent_coordination"] is True
    assert "conversation_id" in call_args


def test_agent_mode_without_message_bus(memgraph_adapter):
    """Test that agent mode requires message bus."""
    with pytest.raises(ValueError) as excinfo:
        memgraph_adapter._execute_agent_query({
            "question": "Test question",
            "kg_id": "test-kg",
            "tenant_id": "tenant-1"
        })

    assert "MessageBusPort is required for agent mode" in str(excinfo.value)


def test_convert_to_domain_triples(memgraph_adapter):
    """Test conversion from Memgraph triples to domain Triple objects."""
    # Input Memgraph triples
    memgraph_triples = [
        {"subject": "Entity1", "predicate": "relatedTo", "object": "Entity2"},
        {"subject": "Entity2", "predicate": "hasProperty", "object": "Value1"},
        # Malformed triple missing required fields
        {"subject": "Entity3", "object": "Value2"}
    ]

    # Convert to domain triples
    result = memgraph_adapter._convert_to_domain_triples(memgraph_triples, "tenant-1")

    # Verify results
    assert len(result) == 2  # Malformed triple should be skipped
    assert isinstance(result[0], Triple)
    assert result[0].subject == "Entity1"
    assert result[0].predicate == "relatedTo"
    assert result[0].object == "Entity2"
    assert result[0].tenant_id == "tenant-1"
    assert result[1].subject == "Entity2"
    assert result[1].predicate == "hasProperty"
    assert result[1].object == "Value1"
    assert result[1].tenant_id == "tenant-1"


def test_format_text_response(memgraph_adapter):
    """Test formatting of text response from query result."""
    # Test with response and reasoning
    result1 = {
        "response": "This is the answer",
        "reasoning": "This is the reasoning"
    }
    formatted1 = memgraph_adapter._format_text_response(result1)
    assert "This is the answer" in formatted1
    assert "Reasoning:" in formatted1
    assert "This is the reasoning" in formatted1

    # Test with response, reasoning, and path
    result2 = {
        "response": "This is the answer",
        "reasoning": "This is the reasoning",
        "path": [
            {"node": "Entity1"},
            {"edge": "relatedTo"},
            {"node": "Entity2"}
        ]
    }
    formatted2 = memgraph_adapter._format_text_response(result2)
    assert "This is the answer" in formatted2
    assert "Reasoning:" in formatted2
    assert "Path Information:" in formatted2
    assert "Node: Entity1" in formatted2
    assert "Edge: relatedTo" in formatted2

    # Test with only response
    result3 = {
        "response": "This is the answer"
    }
    formatted3 = memgraph_adapter._format_text_response(result3)
    assert formatted3 == "This is the answer"

    # Test with empty result
    result4 = {}
    formatted4 = memgraph_adapter._format_text_response(result4)
    assert "No direct answer found" in formatted4


def test_format_path_info(memgraph_adapter):
    """Test formatting of path information for text response."""
    # Test with list of dictionaries
    path1 = [
        {"node": "Entity1"},
        {"edge": "relatedTo"},
        {"node": "Entity2"}
    ]
    formatted1 = memgraph_adapter._format_path_info(path1)
    assert "Node: Entity1" in formatted1
    assert "Edge: relatedTo" in formatted1
    assert "Node: Entity2" in formatted1

    # Test with string
    path2 = "Entity1 -> relatedTo -> Entity2"
    formatted2 = memgraph_adapter._format_path_info(path2)
    assert formatted2 == path2

    # Test with list of strings
    path3 = ["Entity1", "relatedTo", "Entity2"]
    formatted3 = memgraph_adapter._format_path_info(path3)
    assert "Step 1: Entity1" in formatted3
    assert "Step 2: relatedTo" in formatted3
    assert "Step 3: Entity2" in formatted3

    # Test with empty path
    assert memgraph_adapter._format_path_info(None) == ""
    assert memgraph_adapter._format_path_info([]) == ""