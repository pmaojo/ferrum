from __future__ import annotations

import logging
from typing import Any, Dict, List, Union

from application.ports import GraphRetrieverPort
from domain.entities import Triple

from .exceptions import GraphRAGException

logger = logging.getLogger(__name__)


class QueryExecutionService:
    """Run translated queries against the knowledge graph."""

    def __init__(self, retriever: GraphRetrieverPort) -> None:
        self._retriever = retriever

    def run_query(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        query_opts: Dict[str, Any],
    ) -> Union[str, List[Triple]]:
        """Execute query with options and handle errors."""
        default_opts = {
            "max_hops": 2,
            "context_tokens": 4096,
            "return_triples": False,
            "include_reasoning": True,
        }
        default_opts.update(query_opts)

        try:
            return self._retriever.run(
                question=question, kg_id=kg_id, tenant_id=tenant_id, opts=default_opts
            )
        except Exception as exc:  # pragma: no cover - external dependency
            logger.error("GraphRAG query execution failed: %s", exc)
            raise GraphRAGException(
                message=f"Query execution failed: {exc}",
                error_code="QUERY_EXECUTION_FAILED",
                context={
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "question": question[:100],
                    "opts": default_opts,
                },
            ) from exc
