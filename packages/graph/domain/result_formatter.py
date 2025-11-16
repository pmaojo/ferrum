from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from domain.entities import Triple

from .ambiguity_detector import AmbiguityDetector

logger = logging.getLogger(__name__)


class ResultFormatter:
    """Format query results and extract relevant subgraphs."""

    def __init__(self, ambiguity_detector: Optional[AmbiguityDetector] = None) -> None:
        self._ambiguity_detector = ambiguity_detector or AmbiguityDetector()

    # Public API
    def format_response(
        self,
        *,
        results: Union[str, List[Triple]],
        explanation: Optional[str],
        translated_query: str,
        execution_time_ms: float,
        max_results: int,
        subgraph: Optional[Dict[str, Any]] = None,
        clarification_needed: bool = False,
        clarification_questions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if isinstance(results, str):
            formatted_results = self._format_text_results(results, max_results)
        elif isinstance(results, list):
            formatted_results = self._format_triple_results(results, max_results)
        else:
            formatted_results = []

        response = {
            "results": formatted_results,
            "metadata": {
                "execution_time_ms": execution_time_ms,
                "result_count": len(formatted_results),
                "translated_query": translated_query,
                "error": False,
            },
        }
        if explanation:
            response["explanation"] = explanation
        if subgraph:
            response["subgraph"] = subgraph
        if clarification_needed:
            response["clarification_needed"] = True
            if clarification_questions:
                response["clarification_questions"] = clarification_questions
        return response

    def has_meaningful_results(self, results: Union[str, List[Triple]]) -> bool:
        if isinstance(results, str):
            return len(results.strip()) > 10 and not any(
                phrase in results.lower()
                for phrase in ["no results", "not found", "no information", "empty"]
            )
        if isinstance(results, list):
            return len(results) > 0
        return False

    def extract_relevant_subgraph(
        self, *, results: Union[str, List[Triple]], kg_id: str, tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        if isinstance(results, list) and results:
            return self._extract_subgraph_from_triples(results)
        if isinstance(results, str) and results.strip():
            return self._extract_subgraph_from_text(results, kg_id, tenant_id)
        return None

    # Internal helpers
    def _format_text_results(self, results: str, max_results: int) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []
        sentences = results.split(". ")
        for i, sentence in enumerate(sentences[:max_results]):
            if sentence.strip():
                chunks.append(
                    {
                        "type": "text",
                        "content": sentence.strip() + ("" if sentence.endswith(".") else "."),
                        "relevance_score": 1.0 - (i * 0.1),
                        "source": "graphrag_text",
                    }
                )
        return chunks

    def _format_triple_results(self, results: List[Triple], max_results: int) -> List[Dict[str, Any]]:
        formatted: List[Dict[str, Any]] = []
        for i, triple in enumerate(results[:max_results]):
            formatted.append(
                {
                    "type": "triple",
                    "subject": triple.subject,
                    "predicate": triple.predicate,
                    "object": triple.object,
                    "tenant_id": triple.tenant_id,
                    "relevance_score": 1.0 - (i * 0.05),
                    "source": "graphrag_triple",
                }
            )
        return formatted

    def _extract_subgraph_from_triples(self, triples: List[Triple]) -> Dict[str, Any]:
        nodes = set()
        edges = []
        for triple in triples:
            nodes.add(triple.subject)
            nodes.add(triple.object)
            edges.append(
                {
                    "source": triple.subject,
                    "target": triple.object,
                    "relationship": triple.predicate,
                    "tenant_id": triple.tenant_id,
                }
            )
        node_degrees = {
            node: sum(1 for e in edges if e["source"] == node or e["target"] == node)
            for node in nodes
        }
        formatted_nodes = [
            {"id": node, "importance": node_degrees.get(node, 0), "highlight": True}
            for node in nodes
        ]
        return {
            "nodes": formatted_nodes,
            "edges": edges,
            "type": "triple_subgraph",
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def _extract_subgraph_from_text(self, text: str, kg_id: str, tenant_id: str) -> Dict[str, Any]:
        entities = self._ambiguity_detector.extract_potential_entities_from_text(text)
        if not entities:
            return {
                "nodes": [],
                "edges": [],
                "type": "text_subgraph",
                "node_count": 0,
                "edge_count": 0,
                "note": "No specific entities identified for subgraph highlighting",
            }
        nodes = [
            {
                "id": entity,
                "importance": 1.0,
                "highlight": True,
                "source": "text_extraction",
            }
            for entity in entities
        ]
        edges = []
        if len(entities) > 1:
            for i, e1 in enumerate(entities[:-1]):
                for e2 in entities[i + 1 :]:
                    edges.append(
                        {
                            "source": e1,
                            "target": e2,
                            "relationship": "mentioned_together",
                            "tenant_id": tenant_id,
                            "confidence": 0.5,
                        }
                    )
        return {
            "nodes": nodes,
            "edges": edges,
            "type": "text_subgraph",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "extraction_method": "text_analysis",
        }
