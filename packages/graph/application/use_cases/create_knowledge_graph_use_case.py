"""Backwards compatible alias for `CreateKnowledgeGraphUseCase`."""

from .knowledge_graph.create_knowledge_graph_use_case import (
    CreateKnowledgeGraphUseCase,
    KnowledgeGraphRepositoryPort,
)

__all__ = ['CreateKnowledgeGraphUseCase', 'KnowledgeGraphRepositoryPort']
