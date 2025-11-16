"""GraphRetrieverPort implementation using ByoKGQueryEngine."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from application.ports import GraphRetrieverPort
from domain.entities import Triple
from domain.services import GraphRAGException

logger = logging.getLogger(__name__)


class ByoKGRAGAdapter(GraphRetrieverPort):
    """Adapter that delegates GraphRAG operations to ByoKGQueryEngine."""

    def __init__(self, engine: Optional[Any] = None) -> None:
        """Create adapter with optional preconfigured engine."""
        try:
            self._engine = engine or self._create_engine()
        except Exception as err:  # pragma: no cover - defensive
            logger.error("Failed to initialize ByoKGQueryEngine", exc_info=True)
            raise GraphRAGException(
                message="Failed to initialize ByoKGQueryEngine",
                error_code="BYOKG_INIT_ERROR",
                context={"error": str(err)},
            ) from err

    def _create_engine(self) -> Any:
        """Instantiate the default ByoKGQueryEngine."""
        from byokg_rag import ByoKGQueryEngine  # type: ignore

        return ByoKGQueryEngine()

    def index(
        self, *, docs: List[str], kg_id: str, tenant_id: str, **kwargs: Any
    ) -> List[Triple]:
        """Index documents using the underlying engine."""
        try:
            result = self._engine.ingest(
                docs=docs, kg_id=kg_id, tenant_id=tenant_id, **kwargs
            )
            triples_data = result.get("triples", result)
            return self._to_triples(triples_data, tenant_id)
        except Exception as err:
            logger.error("ByoKG ingestion failed", exc_info=True)
            raise GraphRAGException(
                message=f"ByoKG ingestion failed: {err}",
                error_code="BYOKG_INDEX_ERROR",
                context={"kg_id": kg_id, "tenant_id": tenant_id},
            ) from err

    def run(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, List[Triple]]:
        """Execute a natural language query using the engine."""
        options = opts or {}
        try:
            result = self._engine.query(
                question=question, kg_id=kg_id, tenant_id=tenant_id, **options
            )
            if options.get("return_triples"):
                triples_data = result.get("triples", [])
                return self._to_triples(triples_data, tenant_id)
            return result.get("answer", "")
        except Exception as err:
            logger.error("ByoKG query failed", exc_info=True)
            raise GraphRAGException(
                message=f"ByoKG query failed: {err}",
                error_code="BYOKG_QUERY_ERROR",
                context={
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "question": question[:100],
                },
            ) from err

    @staticmethod
    def _to_triples(data: List[Dict[str, Any]], tenant_id: str) -> List[Triple]:
        """Convert raw triple dictionaries to domain Triple objects."""
        triples: List[Triple] = []
        for item in data:
            if all(key in item for key in ("subject", "predicate", "object")):
                triples.append(
                    Triple(
                        subject=item["subject"],
                        predicate=item["predicate"],
                        object=item["object"],
                        tenant_id=tenant_id,
                    )
                )
        return triples
