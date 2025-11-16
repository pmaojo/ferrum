import pytest
from datetime import datetime, timezone

from domain.entities import OntologyVersion, ScientificDomain
from domain.exceptions import VersioningException


def _build_version(version_id: str, parent_id: str | None) -> OntologyVersion:
    return OntologyVersion(
        id=version_id,
        checksum="checksum",
        parent_version=parent_id,
        tenant_id="t1",
        domain=ScientificDomain.GENERAL,
        created_at=datetime.now(timezone.utc),
        axioms=["A"]
    )


def test_lineage_depth_root_version():
    version = _build_version("v1", None)
    assert version.get_version_lineage_depth(lambda _id: None) == 0


def test_lineage_depth_multi_level():
    root = _build_version("root", None)
    child = _build_version("child", root.id)
    grandchild = _build_version("grandchild", child.id)

    mapping = {root.id: root, child.id: child, grandchild.id: grandchild}
    lookup = mapping.get

    assert root.get_version_lineage_depth(lookup) == 0
    assert child.get_version_lineage_depth(lookup) == 1
    assert grandchild.get_version_lineage_depth(lookup) == 2


def test_lineage_depth_cycle_detection():
    v1 = _build_version("v1", "v2")
    v2 = _build_version("v2", "v1")

    mapping = {v1.id: v1, v2.id: v2}
    lookup = mapping.get

    with pytest.raises(VersioningException):
        v1.get_version_lineage_depth(lookup)
