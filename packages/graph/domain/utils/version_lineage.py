from __future__ import annotations

from typing import Callable, Optional, Set

from domain.entities import OntologyVersion
from domain.exceptions import VersioningException


def get_root_version_id(
    version: OntologyVersion,
    lookup: Callable[[str], Optional[OntologyVersion]],
) -> str:
    current_id = version.parent_version
    root_id = version.id
    visited: Set[str] = set()

    while current_id is not None:
        if current_id in visited:
            raise VersioningException(
                message="Cycle detected in ontology version lineage",
                version_id=current_id,
            )
        visited.add(current_id)
        parent = lookup(current_id)
        if parent is None:
            root_id = current_id
            break
        root_id = parent.id
        current_id = parent.parent_version
    return root_id


def share_common_ancestor(
    version1: OntologyVersion,
    version2: OntologyVersion,
    lookup: Callable[[str], Optional[OntologyVersion]],
) -> bool:
    return get_root_version_id(version1, lookup) == get_root_version_id(
        version2, lookup
    )
