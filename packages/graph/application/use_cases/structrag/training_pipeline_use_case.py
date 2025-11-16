"""Use case for generating router training data."""

from typing import Any, Dict, List

from application.ports import StructRAGTrainingPipelinePort


class StructRAGTrainingPipelineUseCase:
    """Generate training data for StructRAG router."""

    def __init__(self, training_port: StructRAGTrainingPipelinePort) -> None:
        self.training_port = training_port

    def execute(self, *, documents: List[str], tenant_id: str) -> List[Dict[str, Any]]:
        if not documents:
            raise ValueError("No documents provided")
        return self.training_port.generate_router_training_data(
            documents=documents, tenant_id=tenant_id
        )
