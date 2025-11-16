"""Simple fallback adapter for GraphRetrieverPort.

This adapter is used when no real graph backend is available.  All
operations return safe defaults while emitting log messages so the rest of
the system can continue to operate without raising exceptions.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from application.ports.graph import GraphRetrieverPort
from domain.entities import Triple

logger = logging.getLogger(__name__)


class FallbackGraphAdapter(GraphRetrieverPort):
    """No-op implementation of :class:`GraphRetrieverPort`."""

    def __init__(self, connection_string: str = "redis://0.0.0.0:6379") -> None:
        self.connection_string = connection_string
        logger.warning(
            "Initializing FallbackGraphAdapter. All graph operations will return empty results."
        )

    # ------------------------------------------------------------------
    # GraphRetrieverPort API
    # ------------------------------------------------------------------
    def index(self, *, docs: List[str], kg_id: str, tenant_id: str) -> List[Triple]:
        """Return an empty list of triples."""

        logger.warning(
            "index() called on FallbackGraphAdapter for kg_id=%s tenant_id=%s",
            kg_id,
            tenant_id,
        )
        return []

    def run(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, List[Triple]]:
        """Return an empty string or list depending on ``opts``."""

        logger.warning(
            "run() called on FallbackGraphAdapter for kg_id=%s tenant_id=%s",
            kg_id,
            tenant_id,
        )
        if opts and opts.get("return_triples"):
            return []
        return ""

    # ------------------------------------------------------------------
    # Additional helper methods used by higher level code
    # ------------------------------------------------------------------
    def retrieve_context(self, query: str, **kwargs) -> List[Triple]:
        logger.warning("retrieve_context() called on FallbackGraphAdapter")
        return []

    def execute_query(self, query: str, **kwargs) -> Dict[str, Any]:
        logger.warning("execute_query() called on FallbackGraphAdapter")
        return {"success": False, "error_message": "Fallback mode", "results": []}

    def test_connection(self) -> bool:
        logger.info("test_connection() called on FallbackGraphAdapter")
        return False

    def close(self) -> None:  # pragma: no cover - nothing to clean up
        logger.info("close() called on FallbackGraphAdapter")
