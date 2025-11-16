"""Simple rule-based query translator implementing QueryTranslatorPort."""

from __future__ import annotations

import re
from typing import Tuple

from application.ports import QueryTranslatorPort


class SimpleQueryTranslatorAdapter(QueryTranslatorPort):
    """Translate natural language into a Cypher pattern search query."""

    def translate(
        self, *, natural_language: str, kg_id: str, tenant_id: str
    ) -> Tuple[str, str]:
        """Convert natural language into a basic Cypher query.

        This implementation performs a naive transformation suitable for simple
        search capabilities. It is intentionally minimal so it can be replaced
        by more sophisticated translators without modifying callers.
        """
        terms = re.findall(r"[\w']+", natural_language.lower())
        if not terms:
            query = "MATCH (n) RETURN n LIMIT 10"
            explanation = "No terms detected; returning first nodes."
            return query, explanation

        pattern = ".*".join(map(re.escape, terms))
        query = (
            "MATCH (n) "
            f"WHERE toLower(n.name) =~ '.*{pattern}.*' "
            "RETURN n LIMIT 50"
        )
        explanation = (
            "Searching for nodes whose name contains the terms: " f"{' '.join(terms)}"
        )
        return query, explanation
