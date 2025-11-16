import logging
from pathlib import Path
from typing import List, Optional, Tuple

import yaml

from domain.entities.triple import Triple
from domain.ontology.kthulu_ontology_loader import KthuluOntologyLoader, ComponentType


class KthuluDocParser:
    """Parses Kthulu requirement documents to ontology triples.

    The parser looks for Markdown files in ``kthulu/docs/requirements`` that
    contain YAML front matter with an ``id`` field and optional ``code_links``.
    For each code link pointing to a use case, the parser emits a triple of the
    form ``(Requirement, satisfiesUseCase, UseCase)``.
    """

    def __init__(
        self,
        base_path: Path | str = Path("kthulu/docs/requirements"),
        ontology_loader: Optional[KthuluOntologyLoader] = None,
    ) -> None:
        self.base_path = Path(base_path)
        self.ontology_loader = ontology_loader or KthuluOntologyLoader()
        self.logger = logging.getLogger(__name__)

    def parse_requirements(self) -> List[Triple]:
        """Parse requirement documents into ontology triples.

        Returns:
            List of ``Triple`` objects linking requirements to use cases.
        """
        triples: List[Triple] = []
        if not self.base_path.exists():
            self.logger.warning("Requirements directory not found: %s", self.base_path)
            return triples

        for md_file in self.base_path.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                if not content.startswith("---"):
                    continue
                _, fm, _ = content.split("---", 2)
                metadata = yaml.safe_load(fm) or {}

                # Handle both formats
                req_id = metadata.get("id") or md_file.stem
                code_links = metadata.get("code_links", [])
                if not code_links:
                    source_file = metadata.get("source_file")
                    if source_file:
                        code_links = [source_file]

                if not req_id or not code_links:
                    continue

                requirement_iri = f"{self.ontology_loader.NAMESPACE}Requirement.{req_id}"

                for link in code_links:
                    # Prioritize explicit metadata, otherwise parse from link
                    module = metadata.get("module")
                    usecase = metadata.get("usecase_name")

                    if not module or not usecase:
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
                            metadata={"source_file": str(md_file)}
                        )
                    )
            except Exception as exc:
                self.logger.warning("Failed to parse %s: %s", md_file, exc)
        return triples

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
