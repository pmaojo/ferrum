"""Simple StructRAG adapter with heuristic implementations.

This adapter provides minimal concrete implementations for all
StructRAG ports defined in :mod:`application.ports.structrag`.
The logic is intentionally lightweight and deterministic so it can
serve as an example and be covered by unit tests without requiring
LLM calls or heavy dependencies.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from application.ports.structrag import (
    StructRAGDecompositionPort,
    StructRAGMultiHopReasoningPort,
    StructRAGRouterPort,
    StructRAGStatisticalAnalysisPort,
    StructRAGStructurizerPort,
    StructRAGTrainingPipelinePort,
)


class SimpleStructRAGAdapter(
    StructRAGRouterPort,
    StructRAGDecompositionPort,
    StructRAGStructurizerPort,
    StructRAGTrainingPipelinePort,
    StructRAGMultiHopReasoningPort,
    StructRAGStatisticalAnalysisPort,
):
    """Concrete adapter implementing StructRAG ports with heuristics."""

    # ---- Router ---------------------------------------------------------
    def select_structure(
        self, *, query: str, documents: List[str], tenant_id: str
    ) -> str:
        """Select a structure type based on simple keyword rules."""
        q = query.lower()
        if any(
            k in q
            for k in [
                "average",
                "sum",
                "total",
                "count",
                "statistics",
                "ratio",
                "percent",
            ]
        ):
            return "table"
        if any(k in q for k in ["relationship", "connect", "graph", "link"]):
            return "graph"
        return "list"

    # ---- Decomposition --------------------------------------------------
    def decompose_question(
        self, *, query: str, documents: List[str], tenant_id: str
    ) -> List[str]:
        """Break a query into subqueries using conjunction keywords."""
        parts = re.split(r"\b(?:and|then)\b", query, flags=re.IGNORECASE)
        subqueries = [p.strip(" ?.,") for p in parts if p.strip()]
        return subqueries

    # ---- Structurizer ---------------------------------------------------
    def structurize(
        self,
        *,
        documents: List[str],
        structure_type: str,
        tenant_id: str,
        data_id: str,
    ) -> str:
        """Return a naive structured representation for the documents."""
        if structure_type == "list":
            return "\n".join(f"- {doc.strip()}" for doc in documents)
        if structure_type == "table":
            rows = [doc.replace(",", ";") for doc in documents]
            header = "value"
            return header + "\n" + "\n".join(rows)
        if structure_type == "graph":
            nodes = {f"doc_{i}": doc for i, doc in enumerate(documents)}
            edges = [
                {"from": f"doc_{i}", "to": f"doc_{i+1}"}
                for i in range(len(documents) - 1)
            ]
            return json.dumps({"nodes": nodes, "edges": edges})
        raise ValueError(f"Unknown structure_type: {structure_type}")

    # ---- Training data generation --------------------------------------
    def generate_router_training_data(
        self, *, documents: List[str], tenant_id: str
    ) -> List[Dict[str, Any]]:
        """Generate training examples by inferring structure for each doc."""
        samples: List[Dict[str, Any]] = []
        for doc in documents:
            query = doc.splitlines()[0]
            structure = self.select_structure(
                query=query, documents=[doc], tenant_id=tenant_id
            )
            samples.append({"query": query, "structure": structure})
        return samples

    # ---- Multi-hop reasoning -------------------------------------------
    def answer(
        self,
        *,
        query: str,
        documents: List[str],
        tenant_id: str,
        max_hops: int = 2,
    ) -> str:
        """Answer a query by searching for keywords from subqueries."""
        subqueries = self.decompose_question(
            query=query, documents=documents, tenant_id=tenant_id
        )
        corpus = " ".join(documents)
        answers: List[str] = []
        for sq in subqueries[:max_hops]:
            words = re.findall(r"\w+", sq.lower())
            keyword = next(
                (w for w in words if w not in {"what", "is", "the", "of", "and", "who"}),
                words[0] if words else "",
            )
            for sentence in re.split(r"[.!?]", corpus):
                if keyword and keyword in sentence.lower():
                    answers.append(sentence.strip())
                    break
        return " ".join(answers) if answers else "No answer found"

    # ---- Statistical analysis -----------------------------------------
    def analyze(
        self, *, query: str, documents: List[str], tenant_id: str
    ) -> Dict[str, Any]:
        """Compute basic statistics over numbers in documents."""
        text = " ".join(documents)
        numbers = [float(n) for n in re.findall(r"-?\d+\.?\d*", text)]
        result: Dict[str, Any] = {"count": len(numbers)}
        if not numbers:
            return result
        if re.search("average|mean", query, re.IGNORECASE):
            result["average"] = sum(numbers) / len(numbers)
        if re.search("sum|total", query, re.IGNORECASE):
            result["sum"] = sum(numbers)
        if re.search("max|highest", query, re.IGNORECASE):
            result["max"] = max(numbers)
        if re.search("min|lowest", query, re.IGNORECASE):
            result["min"] = min(numbers)
        return result
