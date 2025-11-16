"""Example script for using the AutoGen tool registry.

This script demonstrates how to initialize the GraphRAG tools for AutoGen
Studio, execute a simple query and print the results.
"""

from __future__ import annotations

import os
import logging


from adapters.inmemory_message_bus_adapter import InMemoryMessageBusAdapter
from adapters.retrievers.graphrag_adapter import GraphRAGAdapter
from ui_adapters.autogen.graphrag_tool import (
    GraphRAGToolRegistry,
    register_with_autogen,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_tools() -> dict[str, callable]:
    """Initialize GraphRAGToolRegistry and register tools."""
    graph_adapter = GraphRAGAdapter(api_key=os.environ.get("GRAPHRAG_API_KEY"))
    bus = InMemoryMessageBusAdapter()
    registry = GraphRAGToolRegistry(retriever=graph_adapter, message_bus=bus)
    return register_with_autogen(registry)


def main() -> None:
    """Run a sample query using the ask_graphrag tool."""
    tools = initialize_tools()
    ask_graphrag = tools["ask_graphrag"]
    result = ask_graphrag(question="What is GraphRAG?")
    print(result)


if __name__ == "__main__":
    main()
