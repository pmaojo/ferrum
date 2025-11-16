from typing import Any, Dict, List


class StepValidator:
    """Validate workflow step configurations."""

    VALID_TYPES = {"graphrag_query", "graphrag_index", "custom_function", "condition"}

    def validate(self, steps: List[Dict[str, Any]]) -> None:
        if not steps:
            raise ValueError("Workflow must have at least one step")
        for index, step in enumerate(steps):
            if "type" not in step:
                raise ValueError(f"Step {index + 1} missing required 'type' field")
            step_type = step["type"]
            if step_type not in self.VALID_TYPES:
                raise ValueError(f"Step {index + 1} has invalid type: {step_type}")
            if step_type == "graphrag_query" and "question" not in step:
                raise ValueError(
                    f"Step {index + 1} (graphrag_query) missing required 'question' field"
                )
            if step_type == "graphrag_index" and "docs" not in step:
                raise ValueError(
                    f"Step {index + 1} (graphrag_index) missing required 'docs' field"
                )
            if step_type == "custom_function" and "function" not in step:
                raise ValueError(
                    f"Step {index + 1} (custom_function) missing required 'function' field"
                )
