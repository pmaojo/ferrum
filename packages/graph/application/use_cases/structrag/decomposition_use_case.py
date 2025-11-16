"""Use case for decomposing complex questions."""

from typing import List

from application.ports import StructRAGDecompositionPort


class StructRAGDecompositionUseCase:
    """Break queries into subqueries via decomposition port."""

    def __init__(self, decomposer: StructRAGDecompositionPort) -> None:
        self.decomposer = decomposer

    def execute(self, *, query: str, documents: List[str], tenant_id: str) -> List[str]:
        if not query.strip():
            raise ValueError("Query cannot be empty")
        if not documents:
            raise ValueError("No documents provided")
        return self.decomposer.decompose_question(
            query=query, documents=documents, tenant_id=tenant_id
        )
