"""Use case for performing statistical analysis using StructRAG."""

from typing import Any, Dict, List

from application.ports import StructRAGStatisticalAnalysisPort


class StructRAGStatisticalAnalysisUseCase:
    """Perform table-based analysis via analysis port."""

    def __init__(self, analysis_port: StructRAGStatisticalAnalysisPort) -> None:
        self.analysis_port = analysis_port

    def execute(
        self, *, query: str, documents: List[str], tenant_id: str
    ) -> Dict[str, Any]:
        if not query.strip():
            raise ValueError("Query cannot be empty")
        if not documents:
            raise ValueError("No documents provided")
        return self.analysis_port.analyze(
            query=query, documents=documents, tenant_id=tenant_id
        )
