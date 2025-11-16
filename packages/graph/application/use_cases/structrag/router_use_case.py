"""Use case for selecting optimal structure type using StructRAG router."""

from typing import List

from application.ports import StructRAGRouterPort


class StructRAGRouterUseCase:
    """Delegate structure selection to a router port."""

    def __init__(self, router: StructRAGRouterPort) -> None:
        self.router = router

    def execute(self, *, query: str, documents: List[str], tenant_id: str) -> str:
        if not query.strip():
            raise ValueError("Query cannot be empty")
        if not documents:
            raise ValueError("No documents provided")
        return self.router.select_structure(
            query=query, documents=documents, tenant_id=tenant_id
        )
