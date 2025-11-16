import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestStreamlitIntegration:
    """Integration tests for Streamlit app functionality."""

    @patch("streamlit.cache_resource")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key-123"})
    def test_streamlit_app_imports_successfully(self, mock_cache_resource):
        """Test that the Streamlit app can be imported without errors."""
        # Mock streamlit cache_resource decorator
        mock_cache_resource.side_effect = lambda func: func

        # Import should not raise any exceptions
        try:
            import ui_adapters.streamlit_app as streamlit_app
            assert hasattr(streamlit_app, "initialize_services")
            assert hasattr(streamlit_app, "authentication_page")
            assert hasattr(streamlit_app, "query_page")
            assert hasattr(streamlit_app, "main")
        except ImportError as e:
            pytest.fail(f"Failed to import Streamlit app: {e}")

    @patch("streamlit.cache_resource")
    @patch("ui_adapters.streamlit_app.InMemoryTracingAdapter")
    @patch("ui_adapters.streamlit_app.GeminiLLMAdapter")
    @patch("ui_adapters.streamlit_app.FalkorGraphAdapter")
    @patch("ui_adapters.streamlit_app.GraphRAGAdapter")
    @patch("ui_adapters.streamlit_app.QueryService")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key-123"})
    def test_service_initialization_flow(
        self,
        mock_query_service,
        mock_graphrag,
        mock_falkor,
        mock_gemini,
        mock_tracer,
        mock_cache_resource
    ):
        """Test the complete service initialization flow."""
        # Mock streamlit cache_resource decorator
        mock_cache_resource.side_effect = lambda func: func

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

        # Import and test
        from ui_adapters.streamlit_app import initialize_services

        services = initialize_services()

        # Verify all services are properly initialized
        assert services is not None
        assert len(services) == 5

        expected_keys = {
            "query_service", "query_use_case", "gremlin_use_case",
            "graph_adapter", "llm_adapter"
        }
        assert set(services.keys()) == expected_keys

        # Verify services are not None (except gremlin_use_case which depends on graph_adapter)
        assert services["query_service"] is not None
        assert services["query_use_case"] is not None
        assert services["llm_adapter"] is not None
        assert services["graph_adapter"] is not None

    @patch("streamlit.cache_resource")
    @patch("streamlit.warning")
    @patch("ui_adapters.streamlit_app.InMemoryTracingAdapter")
    @patch("ui_adapters.streamlit_app.GeminiLLMAdapter")
    @patch("ui_adapters.streamlit_app.FalkorGraphAdapter")
    @patch("ui_adapters.streamlit_app.GraphRAGAdapter")
    @patch("ui_adapters.streamlit_app.QueryService")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key-123"})
    def test_redis_fallback_behavior(
        self,
        mock_query_service,
        mock_graphrag,
        mock_falkor,
        mock_gemini,
        mock_tracer,
        mock_st_warning,
        mock_cache_resource
    ):
        """Test that the app gracefully handles Redis/FalkorDB unavailability."""
        # Mock streamlit cache_resource decorator
        mock_cache_resource.side_effect = lambda func: func

        # Setup mocks
        mock_tracer_instance = Mock()
        mock_tracer.return_value = mock_tracer_instance

        mock_llm_instance = Mock()
        mock_gemini.return_value = mock_llm_instance

        # Make FalkorDB connection fail
        mock_falkor.side_effect = Exception("Connection refused")

        mock_graphrag_instance = Mock()
        mock_graphrag.return_value = mock_graphrag_instance

        mock_query_service_instance = Mock()
        mock_query_service.return_value = mock_query_service_instance

        # Import and test
        from ui_adapters.streamlit_app import initialize_services

        services = initialize_services()

        # Verify fallback behavior
        assert services is not None
        assert services["graph_adapter"] is None
        assert services["gremlin_use_case"] is None
        assert services["query_use_case"] is not None

        # Verify warning was shown
        mock_st_warning.assert_called_once_with(
            "⚠️ Redis/FalkorDB not available. Some features may be limited."
        )
