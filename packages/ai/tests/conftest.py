import sys
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

# Additional stubs to avoid optional dependencies during testing
if "openai" not in sys.modules:
    openai_stub = types.ModuleType("openai")

    class _Chat:
        @staticmethod
        def create(*_a, **_k):
            raise RuntimeError("openai stub called")

    class _ChatCompletion:
        ChatCompletion = None  # placeholder for IDEs

    openai_stub.ChatCompletion = _ChatCompletion
    openai_stub.ChatCompletion.create = _Chat.create  # type: ignore
    sys.modules["openai"] = openai_stub

if "anthropic" not in sys.modules:
    anthropic_stub = types.ModuleType("anthropic")

    class _Messages:
        def create(self, *_a, **_k):  # pragma: no cover - stub
            raise RuntimeError("anthropic stub called")

    class _Anthropic:
        def __init__(self, *_a, **_k):
            self.messages = _Messages()

    anthropic_stub.Anthropic = _Anthropic
    sys.modules["anthropic"] = anthropic_stub

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")

    class _Response:
        def __init__(self):
            self.status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": ""}}]}

    def _post(*_a, **_k):
        return _Response()

    requests_stub.post = _post
    sys.modules["requests"] = requests_stub
