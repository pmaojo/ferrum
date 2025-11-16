from __future__ import annotations

from typing import List, Optional, Protocol

from domain.entities import OntologyVersion, Triple
from domain.owl_conversion import convert_triples_to_owl


class OntologyVersionRepositoryPort(Protocol):
    """Repository interface for storing ontology versions."""

    def store_version(
        self,
        *,
        axioms: List[str],
        parent_version_id: Optional[str],
        tenant_id: str,
    ) -> OntologyVersion: ...

    def get_version(
        self,
        *,
        version_id: str,
        tenant_id: str,
    ) -> Optional[OntologyVersion]: ...

    def get_version_history(
        self,
        *,
        tenant_id: str,
        limit: int = 10,
    ) -> List[OntologyVersion]: ...

    def delete_version(
        self,
        *,
        version_id: str,
        tenant_id: str,
    ) -> bool: ...


class OntologyVersionService:
    """Service for managing ontology versions."""

    def __init__(self, repository: OntologyVersionRepositoryPort) -> None:
        self._repository = repository

    def store_version(
        self,
        *,
        triples: List[Triple],
        parent_version_id: Optional[str],
        tenant_id: str,
    ) -> OntologyVersion:
        axioms_str = convert_triples_to_owl(triples)
        axioms = [
            line.strip()
            for line in axioms_str.strip().split("\n")
            if line.strip() and not line.startswith("Ontology:")
        ]
        return self._repository.store_version(
            axioms=axioms,
            parent_version_id=parent_version_id,
            tenant_id=tenant_id,
        )

    def get_version(
        self, *, version_id: str, tenant_id: str
    ) -> Optional[OntologyVersion]:
        return self._repository.get_version(version_id=version_id, tenant_id=tenant_id)

    def get_version_history(
        self, *, tenant_id: str, limit: int = 10
    ) -> List[OntologyVersion]:
        return self._repository.get_version_history(tenant_id=tenant_id, limit=limit)

    def delete_version(self, *, version_id: str, tenant_id: str) -> bool:
        return self._repository.delete_version(
            version_id=version_id, tenant_id=tenant_id
        )
