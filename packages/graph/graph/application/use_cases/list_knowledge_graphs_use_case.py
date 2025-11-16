"""Backwards compatible alias for `ListKnowledgeGraphsUseCase`."""

from .knowledge_graph.list_knowledge_graphs_use_case import (
    ListKnowledgeGraphsUseCase,
    KnowledgeGraphFilterParams,
)

__all__ = ['ListKnowledgeGraphsUseCase', 'KnowledgeGraphFilterParams']
