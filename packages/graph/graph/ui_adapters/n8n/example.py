"""Example script for using the n8n UI adapter.

This script demonstrates how to initialize the N8nGraphRAGAdapter,
execute a simple query and print the results.
"""

from __future__ import annotations

import os
import logging


from domain.services import QueryService, WorkflowOrchestrator
from adapters.retrievers.graphrag_adapter import GraphRAGAdapter
from ui_adapters.n8n.n8n_adapter import N8nGraphRAGAdapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_adapter() -> N8nGraphRAGAdapter:
    """Initialize N8nGraphRAGAdapter with default components."""
    graph_adapter = GraphRAGAdapter(api_key=os.environ.get("GRAPHRAG_API_KEY"))
    query_service = QueryService(translator=graph_adapter, retriever=graph_adapter)
    orchestrator = WorkflowOrchestrator(
        retriever=graph_adapter, translator=graph_adapter
    )
    return N8nGraphRAGAdapter(
        query_service=query_service,
        workflow_orchestrator=orchestrator,
        graph_retriever=graph_adapter,
        query_translator=graph_adapter,
    )


def main() -> None:
    """Run a sample query using the adapter."""
    adapter = initialize_adapter()
    result = adapter.query_knowledge_graph(question="What is GraphRAG?")
    print(result)


if __name__ == "__main__":
    main()
