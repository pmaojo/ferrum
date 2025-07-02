"""Helper functions for retrieving nodes from Qdrant using embeddings."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from qdrant_client import QdrantClient


@lru_cache(maxsize=1)
def _get_client() -> QdrantClient:
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    return QdrantClient(url=url)


@lru_cache(maxsize=1)
def _get_model():
    model_name = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name)
    except Exception:
        return None


def search_node(question: str, collection: str = "ferrus-nodes") -> Optional[str]:
    """Return the closest node id for a question using vector search."""
    model = _get_model()
    if model is None:
        return None
    vec = model.encode(question).tolist()
    client = _get_client()
    try:
        hits = client.search(collection_name=collection, query_vector=vec, limit=1)
    except Exception:
        return None
    if not hits:
        return None
    payload = hits[0].payload or {}
    return payload.get("id") or payload.get("name")
