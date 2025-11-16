"""Simple synchronization bridge service placeholder."""
from __future__ import annotations

from typing import Dict, List

_snapshot: List[Dict[str, str]] = []


def persist_initial_snapshot(project_path: str) -> Dict[str, str]:
    """Persist initial project snapshot.

    Parameters
    ----------
    project_path: str
        Path to the project whose snapshot should be persisted.
    """
    # In this simplified placeholder we don't actually read from the path.
    return {"status": "initialized", "project_path": project_path}


def synchronize(mode: str, triples: List[Dict[str, str]]) -> Dict[str, object]:
    """Synchronize triples using the provided mode.

    Parameters
    ----------
    mode: str
        Either ``"full"`` or ``"incremental"``.
    triples: List[Dict[str, str]]
        Triples to persist.
    """
    if mode not in {"full", "incremental"}:
        raise ValueError("mode must be 'full' or 'incremental'")
    return {"status": "synchronized", "mode": mode, "processed": len(triples)}
