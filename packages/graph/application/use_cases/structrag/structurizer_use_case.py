"""Use case for converting documents into structured knowledge."""

from typing import List

from application.ports import StructRAGStructurizerPort


class StructRAGStructurizerUseCase:
    """Convert documents into chosen structure type."""

    def __init__(self, structurizer: StructRAGStructurizerPort) -> None:
        self.structurizer = structurizer

    def execute(
        self,
        *,
        documents: List[str],
        structure_type: str,
        tenant_id: str,
        data_id: str,
    ) -> str:
        if not documents:
            raise ValueError("No documents provided")
        if not structure_type:
            raise ValueError("structure_type is required")
        return self.structurizer.structurize(
            documents=documents,
            structure_type=structure_type,
            tenant_id=tenant_id,
            data_id=data_id,
        )
