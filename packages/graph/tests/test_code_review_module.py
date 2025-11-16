import importlib.util
from pathlib import Path
from unittest.mock import Mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "domain/agents/advanced_ai_agent/code_review.py"
spec = importlib.util.spec_from_file_location("code_review", MODULE_PATH)
code_review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(code_review)

CodeReviewAssistant = code_review.CodeReviewAssistant


def test_generate_code_review_suggestions_fallback():
    message_bus = Mock()
    llm = Mock()
    llm.generate.side_effect = Exception("fail")
    assistant = CodeReviewAssistant(message_bus, llm, "t", lambda o, e: None)
    suggestions = assistant.generate_code_review_suggestions("file.go", "code", {})
    assert suggestions[0].suggestion_type == "improvement"
