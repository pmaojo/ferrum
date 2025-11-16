from datetime import datetime

from domain.entities import OntologyVersion, ScientificDomain, Triple
from domain.ontology_version_service import (
    OntologyVersionRepositoryPort,
    OntologyVersionService,
)


class InMemoryRepo(OntologyVersionRepositoryPort):
    def __init__(self):
        self.stored = None
        self.versions = []
        self.deleted = []

    def store_version(self, *, axioms, parent_version_id, tenant_id):
        self.stored = {
            "axioms": axioms,
            "parent": parent_version_id,
            "tenant": tenant_id,
        }
        return OntologyVersion(
            id="v1",
            checksum="cs",
            parent_version=parent_version_id,
            tenant_id=tenant_id,
            domain=ScientificDomain.GENERAL,
            created_at=datetime.now(),
            axioms=axioms,
        )

    def get_version(self, *, version_id, tenant_id):
        return None

    def get_version_history(self, *, tenant_id, limit=10):
        return self.versions[:limit]

    def delete_version(self, *, version_id, tenant_id):
        self.deleted.append((version_id, tenant_id))
        return True


def test_store_version_converts_and_stores():
    repo = InMemoryRepo()
    service = OntologyVersionService(repo)
    triples = [Triple("s", "p", "o", "t")]
    version = service.store_version(
        triples=triples, parent_version_id=None, tenant_id="t"
    )
    assert repo.stored is not None
    assert "ObjectPropertyAssertion" in "\n".join(repo.stored["axioms"])
    assert version.tenant_id == "t"


def test_get_version_history_delegates_to_repo():
    repo = InMemoryRepo()
    repo.versions = [
        OntologyVersion(
            id="v1",
            checksum="cs",
            parent_version=None,
            tenant_id="t",
            domain=ScientificDomain.GENERAL,
            created_at=datetime.now(),
            axioms=["A"],
        )
    ]
    service = OntologyVersionService(repo)
    history = service.get_version_history(tenant_id="t")
    assert history == repo.versions


def test_delete_version_delegates_to_repo():
    repo = InMemoryRepo()
    service = OntologyVersionService(repo)
    result = service.delete_version(version_id="v1", tenant_id="t")
    assert result is True
    assert repo.deleted == [("v1", "t")]
