"""Basic rule-based SPARQL translator."""

from __future__ import annotations

import re
from typing import Tuple

from application.ports import SparqlTranslatorPort


class SimpleSparqlTranslatorAdapter(SparqlTranslatorPort):
    """Translate natural language into a minimal SPARQL query."""

    def translate(
        self,
        *,
        natural_language: str,
        kg_id: str,
        tenant_id: str,
    ) -> Tuple[str, str]:
        terms = re.findall(r"[\w']+", natural_language.lower())
        if not terms:
            query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
            explanation = "No terms detected; returning first triples."
            return query, explanation

        filters = " && ".join(
            [
                f'(CONTAINS(LCASE(STR(?s)), "{t}") || CONTAINS(LCASE(STR(?o)), "{t}"))'
                for t in terms
            ]
        )
        query = f"SELECT ?s ?p ?o WHERE {{ ?s ?p ?o . FILTER({filters}) }} LIMIT 50"
        explanation = "Searching for triples containing the terms: " + " ".join(terms)
        return query, explanation
