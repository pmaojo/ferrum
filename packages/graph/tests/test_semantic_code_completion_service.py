from unittest.mock import Mock

from domain.services.semantic_code_completion_service import (
    SemanticCodeCompletionService,
    CompletionRequest,
    CompletionContext,
)
from application.ports.base import LLMPort


def test_dependency_injection_completion_included():
    llm = Mock(spec=LLMPort)
    service = SemanticCodeCompletionService(llm=llm)

    context = CompletionContext(
        file_path="service.py",
        cursor_line=0,
        cursor_column=0,
        current_line="",
        preceding_lines=[],
        following_lines=[],
        project_type="general",
        language="python",
    )
    request = CompletionRequest(
        context=context,
        partial_input="",
        completion_type="pattern",
    )

    completions = service.get_completions(request)
    texts = [c.completion_text for c in completions]
    assert any("def __init__(self, repository: Repository)" in text for text in texts)
