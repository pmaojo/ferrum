from __future__ import annotations

import logging
from typing import Tuple

from application.ports import QueryTranslatorPort

logger = logging.getLogger(__name__)


class QueryTranslationService:
    """Handle natural language to graph query translation with fallback."""

    def __init__(self, translator: QueryTranslatorPort) -> None:
        self._translator = translator

    def translate_with_fallback(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        max_retries: int = 2,
    ) -> Tuple[str, str]:
        """Translate query using the provided port with retry and fallback."""
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                logger.debug("Query translation attempt %s", attempt + 1)
                return self._translator.translate(
                    natural_language=question, kg_id=kg_id, tenant_id=tenant_id
                )
            except Exception as exc:  # pragma: no cover - defensive
                last_exception = exc
                logger.warning(
                    "Query translation attempt %s failed: %s", attempt + 1, exc
                )
                if attempt < max_retries:
                    continue
        logger.warning("Query translation failed, using fallback approach")
        return (
            f"MATCH (n) WHERE n.name CONTAINS '{question[:50]}' RETURN n LIMIT 10",
            f"Fallback query search for terms related to: {question[:100]}...",
        )
