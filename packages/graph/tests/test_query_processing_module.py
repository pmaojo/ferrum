import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import Mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "domain/agents/advanced_ai_agent/query_processing.py"
sys.modules.setdefault("networkx", types.ModuleType("networkx"))
spec = importlib.util.spec_from_file_location("query_processing", MODULE_PATH)
query_processing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(query_processing)

QueryProcessor = query_processing.QueryProcessor
QueryType = query_processing.QueryType


def test_classify_component_search():
    processor = QueryProcessor(Mock(), Mock(), Mock(), Mock(), "t", lambda o, e: None)
    assert processor.classify_query("find component Foo") == QueryType.COMPONENT_SEARCH
