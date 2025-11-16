import os
from typing import Any, Dict, Optional, Type

import streamlit as st


def initialize_services(
    llm_cls: Type,
    graph_adapter_cls: Type,
    graphrag_cls: Type,
    tracer_cls: Type,
    query_service_cls: Type,
    query_use_case_cls: Type,
    gremlin_use_case_cls: Type,
    fallback_graph_cls: Type,
) -> Optional[Dict[str, Any]]:
    """Initialize LLM, graph, and query services."""
    try:
        tracer = tracer_cls()

        perplexica_key = os.environ.get("PERPLEXICA_API_KEY")
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if perplexica_key:
            from adapters.llm.perplexica_llm_adapter import PerplexicaLLMAdapter

            llm_adapter = PerplexicaLLMAdapter(api_key=perplexica_key)
        else:
            llm_adapter = llm_cls(api_key=gemini_api_key)

        connection_string = os.environ.get(
            "FALKORDB_CONNECTION_STRING", "redis://0.0.0.0:6379"
        )
        try:
            # Try FalkorDB adapter first
            graph_adapter = graph_adapter_cls(connection_string=connection_string)
            st.success("✅ Connected to FalkorDB successfully!")
        except Exception as e:
            st.warning(f"⚠️ FalkorDB not available ({str(e)}). Using fallback mode.")
            # Fall back to fallback adapter
            try:
                graph_adapter = fallback_graph_cls(connection_string=connection_string)
            except Exception:
                graph_adapter = None
                st.warning("⚠️ Running in limited mode without graph functionality.")

        graphrag_adapter = graphrag_cls(
            host=os.getenv("GRAPHRAG_HOST", "localhost"),
            port=int(os.getenv("GRAPHRAG_PORT", "6379")),
            username=os.getenv("GRAPHRAG_USERNAME"),
            password=os.getenv("GRAPHRAG_PASSWORD"),
            api_key=os.getenv("GRAPHRAG_API_KEY"),
        )

        query_service = query_service_cls(
            translator=graphrag_adapter,
            retriever=graphrag_adapter,
            tracer=tracer,
        )

        query_use_case = query_use_case_cls(
            query_service=query_service,
            retriever_port=graphrag_adapter,
            translator_port=graphrag_adapter,
            tracer_port=tracer,
            llm_port=llm_adapter,
        )

        gremlin_use_case = None
        if graph_adapter and not isinstance(graph_adapter, fallback_graph_cls):
            try:
                gremlin_use_case = gremlin_use_case_cls(traversal_port=graph_adapter)
            except Exception as e:
                st.warning(f"⚠️ Gremlin functionality not available: {e}")
                gremlin_use_case = None

        return {
            "query_service": query_service,
            "query_use_case": query_use_case,
            "gremlin_use_case": gremlin_use_case,
            "graph_adapter": graph_adapter,
            "llm_adapter": llm_adapter,
        }
    except Exception as e:  # pragma: no cover - safety net
        st.error(f"Failed to initialize services: {e}")
        return None
