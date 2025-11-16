"""Use case for multi-hop reasoning over structured knowledge."""

from typing import List

from application.ports import StructRAGMultiHopReasoningPort


class StructRAGMultiHopReasoningUseCase:
    """Perform multi-hop reasoning via dedicated port."""

    def __init__(self, reasoning_port: StructRAGMultiHopReasoningPort) -> None:
        self.reasoning_port = reasoning_port

    def execute(
        self,
        *,
        query: str,
        documents: List[str],
        tenant_id: str,
        max_hops: int = 2,
    ) -> str:
        if not query.strip():
            raise ValueError("Query cannot be empty")
        if max_hops < 1:
            raise ValueError("max_hops must be positive")
        return self.reasoning_port.answer(
            query=query,
            documents=documents,
            tenant_id=tenant_id,
            max_hops=max_hops,
        )
