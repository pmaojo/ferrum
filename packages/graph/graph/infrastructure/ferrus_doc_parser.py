import logging
from pathlib import Path
from typing import List, Optional, Tuple

import yaml

from domain.entities.triple import Triple
from domain.ontology.ferrus_ontology_loader import FerrusOntologyLoader, ComponentType


class FerrusDocParser:
    """Parses Ferrus requirement documents to ontology triples.

    Each Markdown file is expected to contain YAML front matter with an ``id``
    field and ``code_links`` pointing to Rust use case implementations. For each
    link, a triple ``(Requirement, satisfiesUseCase, UseCase)`` is emitted.
    """

    def __init__(
        self,
        base_path: Path | str = Path("ferrum/docs/requirements"),
        ontology_loader: Optional[FerrusOntologyLoader] = None,
    ) -> None:
        self.base_path = Path(base_path)
        self.ontology_loader = ontology_loader or FerrusOntologyLoader()
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Directory-based parsing
    # ------------------------------------------------------------------
    def parse_requirements(self) -> List[Triple]:
        """Parse all requirement documents in ``base_path``."""
        triples: List[Triple] = []
        if not self.base_path.exists():
            self.logger.warning("Requirements directory not found: %s", self.base_path)
            return triples

        for md_file in self.base_path.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                triples.extend(self.parse_content(content, source_file=str(md_file)))
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.warning("Failed to parse %s: %s", md_file, exc)
        return triples

    # ------------------------------------------------------------------
    # Content-based parsing used by API ingestion
    # ------------------------------------------------------------------
    def parse_content(self, content: str, source_file: str = "") -> List[Triple]:
        """Parse a single Markdown document into triples."""
        triples: List[Triple] = []
        if not content.startswith("---"):
            return triples

        try:
            _, fm, _ = content.split("---", 2)
        except ValueError:
            return triples
        metadata = yaml.safe_load(fm) or {}

        req_id = metadata.get("id")
        code_links = metadata.get("code_links", [])
        if not req_id or not code_links:
            return triples

        requirement_iri = f"{self.ontology_loader.NAMESPACE}Requirement.{req_id}"

        for link in code_links:
            module, usecase = self._parse_use_case_from_link(link)
            if not module or not usecase:
                self.logger.warning("Could not determine module/usecase for %s", link)
                continue
            usecase_iri = self.ontology_loader.create_component_iri(
                ComponentType.USECASE, usecase, module
            )
            triples.append(
                Triple(
                    subject=requirement_iri,
                    predicate=f"{self.ontology_loader.NAMESPACE}satisfiesUseCase",
                    object=usecase_iri,
                    metadata={"source_file": source_file} if source_file else {},
                )
            )
        return triples

    # ------------------------------------------------------------------
    def _parse_use_case_from_link(self, link: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract module and use case name from a code link path."""
        parts = Path(link).parts
        module = None
        if "modules" in parts:
            idx = parts.index("modules")
            if len(parts) > idx + 1:
                module = parts[idx + 1]
        name = Path(link).stem
        if not name:
            return module, None
        usecase = "".join(piece.capitalize() for piece in name.split("_"))
        return module, usecase
