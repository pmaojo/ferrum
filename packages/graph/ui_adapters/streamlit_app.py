from dataclasses import dataclass
from typing import Optional

import streamlit as st

# Expose classes for tests to patch
from domain.entities import ScientificDomain  # noqa: F401
from domain.services import QueryService  # noqa: F401
from adapters.llm.gemini_llm_adapter import GeminiLLMAdapter  # noqa: F401
from adapters.llm.qwen_llm_adapter import QwenLLMAdapter  # noqa: F401
from adapters.retrievers.falkordb_graph_adapter import FalkorGraphAdapter  # noqa: F401
from adapters.retrievers.graphrag_sdk_adapter import GraphRAGSDKAdapter  # noqa: F401
from adapters.retrievers.fallback_graph_adapter import FallbackGraphAdapter  # noqa: F401
from adapters.structrag_adapter import StructRAGAdapter  # noqa: F401
from adapters.inmemory_tracing_adapter import InMemoryTracingAdapter  # noqa: F401
from application.use_cases.execute_gremlin_query_use_case import ExecuteGremlinQueryUseCase  # noqa: F401
from application.use_cases.knowledge_graph.query_knowledge_graph_use_case import (
    QueryKnowledgeGraphUseCase,  # noqa: F401
)

from ui_adapters.streamlit.services import initialize_services as _initialize_services
from ui_adapters.streamlit.auth import authentication_page as _authentication_page
from ui_adapters.streamlit.query import query_page as _query_page
from ui_adapters.streamlit.indexing import indexing_interface as _indexing_interface
from ui_adapters.streamlit.main import main as _main
from ui_adapters.streamlit.ecommerce_platform import main as _ecommerce_main
from domain.unified_agent_coordinator import (  # noqa: F401
    UnifiedAgentCoordinator,
    AgentSystemType,
    UnifiedAgentRequest,
)


@dataclass
class ExecuteGremlinQueryRequest:
    """Request to execute a Gremlin query."""

    query: str
    kg_id: str
    tenant_id: str
    user_id: str
    timeout_seconds: int = 30


@dataclass
class ExecuteGremlinQueryResponse:
    """Response from Gremlin query execution."""

    results: list
    success: bool
    error_message: Optional[str] = None
    processing_time_ms: float = 0.0


# Wrappers exposing the refactored functionality


@st.cache_resource
def initialize_services():
    """Initialize LLM, graph, and query services."""
    return _initialize_services(
        llm_cls=GeminiLLMAdapter,
        graph_adapter_cls=FalkorGraphAdapter,
        graphrag_cls=GraphRAGSDKAdapter,
        tracer_cls=InMemoryTracingAdapter,
        query_service_cls=QueryService,
        query_use_case_cls=QueryKnowledgeGraphUseCase,
        gremlin_use_case_cls=ExecuteGremlinQueryUseCase,
        fallback_graph_cls=FallbackGraphAdapter)


authentication_page = _authentication_page
query_page = _query_page
indexing_interface = _indexing_interface
main = _main
ecommerce_main = _ecommerce_main

if __name__ == "__main__":
    main()
