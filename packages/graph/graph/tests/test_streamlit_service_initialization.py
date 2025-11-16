import pytest
pytest.importorskip("redis")
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestStreamlitServiceInitialization:
    """Test cases for Streamlit service initialization."""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("ui_adapters.streamlit_app.GeminiLLMAdapter")
    @patch("ui_adapters.streamlit_app.FalkorGraphAdapter")
    @patch("ui_adapters.streamlit_app.GraphRAGSDKAdapter")
    @patch("ui_adapters.streamlit_app.InMemoryTracingAdapter")
    @patch("ui_adapters.streamlit_app.QueryService")
    def test_initialize_services_success(
        self,
        mock_query_service,
        mock_tracer,
        mock_graphrag,
        mock_falkor,
        mock_gemini
    ):
        """Test successful service initialization."""
        from ui_adapters.streamlit_app import initialize_services

        # Setup mocks
        mock_tracer_instance = Mock()
        mock_tracer.return_value = mock_tracer_instance

        mock_llm_instance = Mock()
        mock_gemini.return_value = mock_llm_instance

        mock_graph_instance = Mock()
        mock_falkor.return_value = mock_graph_instance

        mock_graphrag_instance = Mock()
        mock_graphrag.return_value = mock_graphrag_instance

        mock_query_service_instance = Mock()
        mock_query_service.return_value = mock_query_service_instance

        # Execute
        services = initialize_services()

        # Verify
        assert services is not None
        assert "query_service" in services
        assert "query_use_case" in services
        assert "gremlin_use_case" in services
        assert "graph_adapter" in services
        assert "llm_adapter" in services

        # Verify QueryKnowledgeGraphUseCase is initialized with correct parameters
        assert services["query_use_case"] is not None

        # Verify adapters were initialized
        mock_gemini.assert_called_once_with(api_key="test-key")
        mock_graphrag.assert_called_once()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("ui_adapters.streamlit_app.GeminiLLMAdapter")
    @patch("ui_adapters.streamlit_app.FalkorGraphAdapter")
    @patch("ui_adapters.streamlit_app.GraphRAGSDKAdapter")
    @patch("ui_adapters.streamlit_app.InMemoryTracingAdapter")
    @patch("ui_adapters.streamlit_app.QueryService")
    def test_initialize_services_with_redis_failure(
        self,
        mock_query_service,
        mock_tracer,
        mock_graphrag,
        mock_falkor,
        mock_gemini
    ):
        """Test service initialization when Redis/FalkorDB is not available."""
        from ui_adapters.streamlit_app import initialize_services

        # Setup mocks
        mock_tracer_instance = Mock()
        mock_tracer.return_value = mock_tracer_instance

        mock_llm_instance = Mock()
        mock_gemini.return_value = mock_llm_instance

        # Make FalkorDB fail
        mock_falkor.side_effect = Exception("Redis connection failed")

        mock_graphrag_instance = Mock()
        mock_graphrag.return_value = mock_graphrag_instance

        mock_query_service_instance = Mock()
        mock_query_service.return_value = mock_query_service_instance

        # Execute
        services = initialize_services()

        # Verify services still initialize without graph adapter
        assert services is not None
        assert services["graph_adapter"] is None
        assert services["gremlin_use_case"] is None
        assert services["query_use_case"] is not None

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("ui_adapters.streamlit_app.GeminiLLMAdapter")
    @patch("ui_adapters.streamlit_app.GraphRAGSDKAdapter")
    def test_initialize_services_critical_failure(
        self,
        mock_graphrag,
        mock_gemini
    ):
        """Test service initialization with critical component failure."""
        from ui_adapters.streamlit_app import initialize_services

        # Make GraphRAG fail
        mock_graphrag.side_effect = Exception("Critical GraphRAG failure")

        # Execute
        services = initialize_services()

        # Verify failure is handled gracefully
        assert services is None

    def test_query_knowledge_graph_use_case_constructor_parameters(self):
        """Test that QueryKnowledgeGraphUseCase requires all expected parameters."""
        from application.use_cases.knowledge_graph.query_knowledge_graph_use_case import QueryKnowledgeGraphUseCase
        from domain.services import QueryService
        from adapters.retrievers.graphrag_adapter import GraphRAGAdapter
        from adapters.llm.gemini_llm_adapter import GeminiLLMAdapter
        from adapters.inmemory_tracing_adapter import InMemoryTracingAdapter

        # Create mock dependencies
        query_service = Mock(spec=QueryService)
        retriever_port = Mock()
        translator_port = Mock()
        tracer_port = Mock(spec=InMemoryTracingAdapter)
        llm_port = Mock(spec=GeminiLLMAdapter)

        # Verify constructor accepts all required parameters
        use_case = QueryKnowledgeGraphUseCase(
            query_service=query_service,
            retriever_port=retriever_port,
            translator_port=translator_port,
            tracer_port=tracer_port,
            llm_port=llm_port
        )

        assert use_case.query_service == query_service
        assert use_case.retriever_port == retriever_port
        assert use_case.translator_port == translator_port
        assert use_case.tracer_port == tracer_port
        assert use_case.llm_port == llm_port

    def test_query_knowledge_graph_use_case_missing_parameters(self):
        """Test that QueryKnowledgeGraphUseCase fails with missing parameters."""
        from application.use_cases.knowledge_graph.query_knowledge_graph_use_case import QueryKnowledgeGraphUseCase

        # Verify constructor fails when parameters are missing
        with pytest.raises(TypeError) as exc_info:
            QueryKnowledgeGraphUseCase()

        error_msg = str(exc_info.value)
        assert "missing" in error_msg
        assert "required positional argument" in error_msg

    def test_execute_gremlin_query_use_case_constructor_parameters(self):
        """Test that ExecuteGremlinQueryUseCase requires expected parameters."""
        from application.use_cases.execute_gremlin_query_use_case import ExecuteGremlinQueryUseCase
        from application.ports import GraphTraversalPort

        # Create mock dependencies
        traversal_port = Mock(spec=GraphTraversalPort)

        # Verify constructor accepts required parameter
        use_case = ExecuteGremlinQueryUseCase(
            traversal_port=traversal_port
        )

        assert use_case._traversal_port == traversal_port

    def test_streamlit_service_initialization_complete(self):
        """Test complete service initialization as done in Streamlit app."""
        from ui_adapters.streamlit_app import initialize_services
        from unittest.mock import patch, Mock
        import os

        # Mock environment variables
        with patch.dict(os.environ, {
            'GEMINI_API_KEY': 'test-key',
            'FALKORDB_CONNECTION_STRING': 'redis://localhost:6379'
        }):
            # Mock Redis connection to avoid actual connection
            with patch('adapters.retrievers.falkordb_graph_adapter.FalkorGraphAdapter') as mock_graph_adapter:
                mock_graph_adapter.return_value = Mock()

                # Call initialization
                services = initialize_services()

                # Verify services are returned
                assert services is not None
                assert 'query_service' in services
                assert 'query_use_case' in services
                assert 'gremlin_use_case' in services
                assert 'graph_adapter' in services
                assert 'llm_adapter' in services