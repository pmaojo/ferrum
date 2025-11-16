"""Port for parsing natural language requirements into validation rules."""
from typing import List, Protocol, TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from application.use_cases.requirements.generate_requirement_contracts_use_case import ValidationRule
else:  # pragma: no cover - runtime
    ValidationRule = Any  # type: ignore


class RequirementParserPort(Protocol):
    """Port responsible for turning raw requirement text into validation rules."""

    def parse(self, requirements: str) -> List[ValidationRule]:
        """Parse requirement clauses into validation rules."""
        ...
