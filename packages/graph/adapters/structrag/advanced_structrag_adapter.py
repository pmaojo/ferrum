"""Adapter implementing advanced StructRAG ports."""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from application.ports import (
    LLMPort,
    StructRAGDecompositionPort,
    StructRAGMultiHopReasoningPort,
    StructRAGRouterPort,
    StructRAGStatisticalAnalysisPort,
    StructRAGStructurizerPort,
    StructRAGTrainingPipelinePort,
    TracingPort,
)
from domain.structrag.structrag_orchestrator import (
    AnalysisAgent,
    ConstructionAgent,
    StructRAGOrchestrator,
)

logger = logging.getLogger(__name__)


class StructRAGAdvancedAdapter(
    StructRAGRouterPort,
    StructRAGDecompositionPort,
    StructRAGStructurizerPort,
    StructRAGTrainingPipelinePort,
    StructRAGMultiHopReasoningPort,
    StructRAGStatisticalAnalysisPort,
):
    """Concrete adapter delegating to StructRAG orchestrator."""

    def __init__(
        self,
        llm: LLMPort,
        tracer: Optional[TracingPort] = None,
        storage_path: str = "./structrag_storage",
    ) -> None:
        self.tracer = tracer
        self.llm = llm
        self.orchestrator = StructRAGOrchestrator(
            llm=llm, tracer=tracer, storage_path=storage_path
        )
        self.analysis_agent = AnalysisAgent(llm, tracer)
        self.construction_agent = ConstructionAgent(llm, Path(storage_path), tracer)

    # ---- Router ----
    def select_structure(
        self, *, query: str, documents: List[str], tenant_id: str
    ) -> str:
        kb_info = self._extract_kb_info(documents)
        _, structure = self.analysis_agent.analyze(
            query=query,
            kb_info=kb_info,
            data_id=f"{tenant_id}_{hash(query)}",
            tenant_id=tenant_id,
        )
        return structure

    # ---- Decomposition ----
    def decompose_question(
        self, *, query: str, documents: List[str], tenant_id: str
    ) -> List[str]:
        kb_info = self._extract_kb_info(documents)
        subqueries, _ = self.analysis_agent.analyze(
            query=query,
            kb_info=kb_info,
            data_id=f"{tenant_id}_{hash(query)}",
            tenant_id=tenant_id,
        )
        return subqueries

    # ---- Structurizer ----
    def structurize(
        self,
        *,
        documents: List[str],
        structure_type: str,
        tenant_id: str,
        data_id: str,
    ) -> str:
        instruction, _ = self.construction_agent.construct(
            subqueries=[],
            chosen_structure=structure_type,
            documents=documents,
            data_id=data_id,
            tenant_id=tenant_id,
        )
        return instruction

    # ---- Training ----
    def generate_router_training_data(
        self, *, documents: List[str], tenant_id: str
    ) -> List[Dict[str, Any]]:
        training_samples: List[Dict[str, Any]] = []
        for doc in documents:
            query = doc.split("\n", 1)[0]
            structure = self.select_structure(
                query=query, documents=[doc], tenant_id=tenant_id
            )
            training_samples.append({"query": query, "structure": structure})
        return training_samples

    # ---- Multi-hop reasoning ----
    def answer(
        self,
        *,
        query: str,
        documents: List[str],
        tenant_id: str,
        max_hops: int = 2,
    ) -> str:
        result = self.orchestrator.process_query(
            query=query,
            documents=documents,
            tenant_id=tenant_id,
            opts={"max_iterations": max_hops},
        )
        return result["answer"]

    # ---- Statistical analysis ----
    def analyze(
        self, *, query: str, documents: List[str], tenant_id: str
    ) -> Dict[str, Any]:
        result = self.orchestrator.process_query(
            query=query,
            documents=documents,
            tenant_id=tenant_id,
            opts={"structure_type": "table"},
        )
        numbers = re.findall(r"[-+]?\d*\.?\d+", " ".join(result["subqueries"]))
        nums = [float(n) for n in numbers]
        avg = sum(nums) / len(nums) if nums else None
        return {"answer": result["answer"], "average": avg}

    # ---- Helpers ----
    def _extract_kb_info(self, documents: List[str]) -> str:
        titles = []
        for doc in documents:
            if "\n\n" in doc:
                titles.append(doc.split("\n\n")[0].strip())
            else:
                titles.append(doc.split("\n")[0].strip())
        return "The titles of the docs are:\n" + "\n".join(set(titles))
