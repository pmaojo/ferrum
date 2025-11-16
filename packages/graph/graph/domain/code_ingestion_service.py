from __future__ import annotations

"""Service orchestrating code analysis and validation."""

from typing import Dict, Iterable, Iterator, List

from application.ports import CodeOntologyPort
from domain.entities import Triple, ValidationReport

from .ingestion_service import IngestionService


class CodeIngestionService:
    """Ingest source code repositories into the knowledge graph."""

    def __init__(
        self, *, analyzer: CodeOntologyPort, ingestion_service: IngestionService
    ) -> None:
        self._analyzer = analyzer
        self._ingestion_service = ingestion_service

    def stream_ingest_repository(
        self,
        *,
        files_iterable: Iterable[str],
        repo_id: str,
        tenant_id: str,
    ) -> Iterator[Triple]:
        """Yield triples incrementally from an iterable of file contents."""

        for content in files_iterable:
            yield from self._analyzer.extract_triples(
                code=content,
                repo_id=repo_id,
                tenant_id=tenant_id,
            )

    def ingest_repository(
        self,
        *,
        files: Dict[str, str],
        repo_id: str,
        tenant_id: str,
        ontology_version_id: str,
        validate_incrementally: bool = True,
    ) -> ValidationReport:
        triples = list(
            self.stream_ingest_repository(
                files_iterable=files.values(),
                repo_id=repo_id,
                tenant_id=tenant_id,
            )
        )

        return self._ingestion_service.validate_triples(
            triples=triples,
            ontology_version_id=ontology_version_id,
            tenant_id=tenant_id,
            validate_incrementally=validate_incrementally,
        )

