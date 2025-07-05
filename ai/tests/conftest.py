import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
AI_DIR = os.path.join(ROOT, "ai")
if AI_DIR not in sys.path:
    sys.path.insert(0, AI_DIR)
os.environ["PYTHONPATH"] = os.pathsep.join(
    [ROOT, AI_DIR, os.environ.get("PYTHONPATH", "")]
)
import types

# Provide lightweight stubs for optional heavy dependencies
if "neo4j" not in sys.modules:
    neo4j_stub = types.ModuleType("neo4j")

    class _GraphDatabase:
        @staticmethod
        def driver(*_a, **_k):
            raise RuntimeError("GraphDatabase stub called")

    neo4j_stub.GraphDatabase = _GraphDatabase
    sys.modules["neo4j"] = neo4j_stub

if "qdrant_client" not in sys.modules:
    qdrant_stub = types.ModuleType("qdrant_client")

    class _QdrantClient:
        def __init__(self, *a, **k):
            pass

        def search(self, *a, **k):
            return []

    qdrant_stub.QdrantClient = _QdrantClient
    sys.modules["qdrant_client"] = qdrant_stub

if "sentence_transformers" not in sys.modules:
    st_stub = types.ModuleType("sentence_transformers")

    class _SentenceTransformer:
        def __init__(self, *a, **k):
            pass

        def encode(self, *_a, **_k):
            return [0.0]

    st_stub.SentenceTransformer = _SentenceTransformer
    sys.modules["sentence_transformers"] = st_stub
