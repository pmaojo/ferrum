import json
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from application.ports.base import MessageBusPort, LLMPort

logger = logging.getLogger(__name__)


@dataclass
class CodeReviewSuggestion:
    """AI-powered code review suggestion"""

    file_path: str
    line_number: Optional[int]
    suggestion_type: str
    title: str
    description: str
    code_snippet: Optional[str]
    suggested_fix: Optional[str]
    confidence: float
    architectural_impact: str


@dataclass
class SemanticCompletion:
    """Semantic code completion suggestion"""

    completion_text: str
    completion_type: str
    description: str
    architectural_context: str
    confidence: float
    imports_needed: List[str]


class CodeReviewAssistant:
    """Generate code review suggestions and semantic completions."""

    def __init__(
        self,
        message_bus: MessageBusPort,
        llm: LLMPort,
        tenant_id: str,
        error_handler,
    ) -> None:
        self.message_bus = message_bus
        self.llm = llm
        self.tenant_id = tenant_id
        self.error_handler = error_handler
        self.review_count = 0
        self.completion_count = 0

    # Code review ----------------------------------------------------
    def handle_code_review_request(self, message: Dict[str, Any]) -> None:
        if not message:
            return
        file_path = message.get("file_path", "")
        code_content = message.get("code_content", "")
        context = message.get("context", {})
        try:
            suggestions = self.generate_code_review_suggestions(
                file_path, code_content, context
            )
            self.message_bus.publish(
                topic="ai.code_review_response",
                message={
                    "file_path": file_path,
                    "suggestions": [
                        {
                            "line_number": s.line_number,
                            "suggestion_type": s.suggestion_type,
                            "title": s.title,
                            "description": s.description,
                            "suggested_fix": s.suggested_fix,
                            "confidence": s.confidence,
                            "architectural_impact": s.architectural_impact,
                        }
                        for s in suggestions
                    ],
                    "tenant_id": self.tenant_id,
                    "timestamp": datetime.now().isoformat(),
                },
                tenant_id=self.tenant_id,
            )
            self.review_count += 1
            logger.info(
                "Generated %d code review suggestions for %s",
                len(suggestions),
                file_path,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Error handling code review request: %s", exc)
            self.error_handler("code_review", str(exc))

    def generate_code_review_suggestions(
        self, file_path: str, code_content: str, context: Dict[str, Any]
    ) -> List[CodeReviewSuggestion]:
        suggestions: List[CodeReviewSuggestion] = []
        review_prompt = f"""
        Review this Go code for architectural and design issues:

        File: {file_path}
        Code:
        ```go
        {code_content}
        ```

        Context: {json.dumps(context, indent=2)}

        Focus on:
        1. Hexagonal architecture violations
        2. Dependency inversion principle
        3. SOLID principles
        4. Domain-driven design issues
        5. Code smells and anti-patterns

        Return JSON array of suggestions with:
        - line_number (if applicable)
        - suggestion_type: "improvement", "bug", "pattern", "architecture"
        - title: brief title
        - description: detailed explanation
        - suggested_fix: specific code fix (if applicable)
        - confidence: 0.0-1.0
        - architectural_impact: "low", "medium", "high"
        """
        try:
            llm_response = self.llm.generate(review_prompt, self.tenant_id)
            suggestions_data = json.loads(llm_response)
            for data in suggestions_data:
                suggestions.append(
                    CodeReviewSuggestion(
                        file_path=file_path,
                        line_number=data.get("line_number"),
                        suggestion_type=data.get("suggestion_type", "improvement"),
                        title=data.get("title", ""),
                        description=data.get("description", ""),
                        code_snippet=None,
                        suggested_fix=data.get("suggested_fix"),
                        confidence=data.get("confidence", 0.5),
                        architectural_impact=data.get("architectural_impact", "medium"),
                    )
                )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error generating code review suggestions: %s", exc)
            suggestions.append(
                CodeReviewSuggestion(
                    file_path=file_path,
                    line_number=None,
                    suggestion_type="improvement",
                    title="Code review analysis failed",
                    description="Unable to analyze code automatically. Consider manual review.",
                    code_snippet=None,
                    suggested_fix=None,
                    confidence=0.3,
                    architectural_impact="low",
                )
            )
        return suggestions

    # Semantic completion -------------------------------------------
    def handle_semantic_completion_request(self, message: Dict[str, Any]) -> None:
        file_path = message.get("file_path", "")
        cursor_position = message.get("cursor_position", {})
        code_context = message.get("code_context", "")
        partial_input = message.get("partial_input", "")
        try:
            completions = self.generate_semantic_completions(
                file_path, cursor_position, code_context, partial_input
            )
            self.message_bus.publish(
                topic="ai.semantic_completion_response",
                message={
                    "file_path": file_path,
                    "completions": [
                        {
                            "completion_text": c.completion_text,
                            "completion_type": c.completion_type,
                            "description": c.description,
                            "architectural_context": c.architectural_context,
                            "confidence": c.confidence,
                            "imports_needed": c.imports_needed,
                        }
                        for c in completions
                    ],
                    "tenant_id": self.tenant_id,
                    "timestamp": datetime.now().isoformat(),
                },
                tenant_id=self.tenant_id,
            )
            self.completion_count += 1
            logger.info(
                "Generated %d semantic completions for %s",
                len(completions),
                file_path,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Error handling semantic completion request: %s", exc)
            self.error_handler("semantic_completion", str(exc))

    def generate_semantic_completions(
        self,
        file_path: str,
        cursor_position: Dict[str, Any],
        code_context: str,
        partial_input: str,
    ) -> List[SemanticCompletion]:
        completions: List[SemanticCompletion] = []
        completion_prompt = f"""
        Generate semantic code completions for Go code following hexagonal architecture:

        File: {file_path}
        Context:
        ```go
        {code_context}
        ```

        Partial input: "{partial_input}"
        Cursor position: {cursor_position}

        Consider:
        1. Hexagonal architecture patterns
        2. Domain-driven design
        3. Interface definitions
        4. Dependency injection
        5. Common Go patterns

        Return JSON array of completions:
        [{{
            "completion_text": "complete code",
            "completion_type": "method|class|interface|pattern",
            "description": "what this completion does",
            "architectural_context": "how it fits in architecture",
            "confidence": 0.0-1.0,
            "imports_needed": ["package1", "package2"]
        }}]

        Limit to 5 most relevant completions.
        """
        try:
            llm_response = self.llm.generate(completion_prompt, self.tenant_id)
            completions_data = json.loads(llm_response)
            for data in completions_data:
                completions.append(
                    SemanticCompletion(
                        completion_text=data.get("completion_text", ""),
                        completion_type=data.get("completion_type", "method"),
                        description=data.get("description", ""),
                        architectural_context=data.get("architectural_context", ""),
                        confidence=data.get("confidence", 0.5),
                        imports_needed=data.get("imports_needed", []),
                    )
                )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error generating semantic completions: %s", exc)
            completions.append(
                SemanticCompletion(
                    completion_text=partial_input + "...",
                    completion_type="fallback",
                    description="Basic completion (AI analysis failed)",
                    architectural_context="Unknown",
                    confidence=0.2,
                    imports_needed=[],
                )
            )
        return completions
