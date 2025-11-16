"""
Example script for running the Chainlit UI adapter.

This script demonstrates how to initialize and run the Chainlit UI adapter
for the GraphRAG Ontology Application.
"""

import os
import logging


# Import required components
from domain.services import QueryService
from domain.graph_visualizer import GraphVisualizer
from adapters.retrievers.graphrag_adapter import GraphRAGAdapter
from adapters.retrievers.falkordb_graph_adapter import FalkorGraphAdapter
from adapters.retrievers.websocket_graph_stream_adapter import WebSocketGraphStreamAdapter
from adapters.louvain_clustering_adapter import LouvainClusteringAdapter
from adapters.opentelemetry_tracing_adapter import OpenTelemetryTracingAdapter
from ui_adapters.chainlit.graphrag_tool import ChainlitGraphRAGAdapter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_adapter():
    """Initialize the Chainlit adapter with required dependencies.

    In a real application, these would be injected through a dependency
    injection container or configuration.

    Returns:
        ChainlitGraphRAGAdapter instance
    """
    try:
        # Initialize adapters
        graph_adapter = FalkorGraphAdapter(connection_string="redis://localhost:6379")
        graphrag_adapter = GraphRAGAdapter(config={"api_key": os.environ.get("GRAPHRAG_API_KEY")})
        tracing_adapter = OpenTelemetryTracingAdapter(service_name="graphrag-chainlit")
        clustering_adapter = LouvainClusteringAdapter(falkor_client=graph_adapter.client)
        stream_adapter = WebSocketGraphStreamAdapter(
            tracing_adapter=tracing_adapter,
            clustering_adapter=clustering_adapter
        )

        # Initialize domain services
        graph_visualizer = GraphVisualizer(
            clustering_port=clustering_adapter,
            stream_port=stream_adapter,
            tracer=tracing_adapter
        )

        query_service = QueryService(
            translator=graphrag_adapter,
            retriever=graphrag_adapter,
            tracer=tracing_adapter
        )

        # Initialize Chainlit adapter
        chainlit_adapter = ChainlitGraphRAGAdapter(
            query_service=query_service,
            graph_retriever=graphrag_adapter,
            query_translator=graphrag_adapter,
            graph_visualizer=graph_visualizer,
            default_kg_id="default",
            default_tenant_id="default"
        )

        logger.info("Chainlit adapter initialized successfully")
        return chainlit_adapter

    except Exception as e:
        logger.error(f"Failed to initialize Chainlit adapter: {str(e)}", exc_info=True)
        raise

# Initialize adapter when imported
adapter = initialize_adapter()

# Note: Chainlit will automatically discover and use the hooks defined in graphrag_tool.py