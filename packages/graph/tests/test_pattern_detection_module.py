import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import Mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "domain/agents/advanced_ai_agent/pattern_detection.py"
sys.modules.setdefault("networkx", types.ModuleType("networkx"))
spec = importlib.util.spec_from_file_location("pattern_detection", MODULE_PATH)
pattern_detection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pattern_detection)

PatternDetector = pattern_detection.PatternDetector
PatternType = pattern_detection.PatternType


def test_calculate_severity():
    detector = PatternDetector(Mock(), Mock(), "t", lambda o, e: None)
    ap = Mock()
    ap.pattern_type = PatternType.CIRCULAR_DEPENDENCY
    assert detector._calculate_severity(ap) == "high"
