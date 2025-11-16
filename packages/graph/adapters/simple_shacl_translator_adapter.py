"""Baseline translator from natural language to SHACL shapes."""

from __future__ import annotations

import re
from typing import Tuple

from application.ports import ShaclTranslatorPort


class SimpleShaclTranslatorAdapter(ShaclTranslatorPort):
    """Translate simple constraint sentences into SHACL."""

    def translate(
        self,
        *,
        natural_language: str,
        kg_id: str,
        tenant_id: str,
    ) -> Tuple[str, str]:
        match = re.search(r"(\w+) must have (\w+)", natural_language, re.I)
        if not match:
            explanation = (
                "Could not detect constraint pattern; returning empty SHACL shape."
            )
            return "# Unable to translate to SHACL", explanation

        cls, prop = match.group(1), match.group(2)
        shape = f"""
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.com/{kg_id}#> .

ex:{cls}Shape
    a sh:NodeShape ;
    sh:targetClass ex:{cls} ;
    sh:property [
        sh:path ex:{prop} ;
        sh:minCount 1 ;
    ] .
"""
        explanation = f"Ensure every {cls} has at least one {prop} property."
        return shape.strip(), explanation
