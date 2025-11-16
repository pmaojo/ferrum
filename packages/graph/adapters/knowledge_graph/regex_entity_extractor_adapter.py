from __future__ import annotations

import re
from typing import Any, Dict, List

from application.use_cases.knowledge_graph.entity_extraction_use_case import (
    EntityExtractionPort,
    ExtractionConfig,
)


class RegexEntityExtractorAdapter(EntityExtractionPort):
    """Very simple regex-based entity extractor."""

    async def extract(
        self,
        *,
        documents: List[str],
        config: ExtractionConfig,
        kg_id: str,
        tenant_id: str,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        pattern = re.compile("|".join(config.entity_types), re.IGNORECASE)
        entities: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []
        for doc in documents:
            for match in pattern.finditer(doc):
                entities.append(
                    {"text": match.group(), "start": match.start(), "end": match.end()}
                )
        # Relationships are mocked for brevity
        for rel in config.relationship_patterns:
            relationships.append({"pattern": rel})
        return entities, relationships
