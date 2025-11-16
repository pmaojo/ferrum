"""Use case for generating competency questions."""

from dataclasses import dataclass
from typing import List

from application.exceptions import ValidationError
from application.ports import CompetencyQuestionPort
from application.use_cases.base_use_case import BaseUseCase


@dataclass
class GenerateCompetencyQuestionsRequest:
    """Input for competency question generation."""

    context: str
    tenant_id: str
    num_questions: int = 10


@dataclass
class CompetencyQuestion:
    """Represents a competency question with identifier."""

    id: str
    question: str


@dataclass
class GenerateCompetencyQuestionsResponse:
    """Competency question generation result."""

    competency_questions: List[CompetencyQuestion]


class GenerateCompetencyQuestionsUseCase(
    BaseUseCase[
        GenerateCompetencyQuestionsRequest,
        GenerateCompetencyQuestionsResponse,
    ]
):
    """Generate competency questions using the configured generator port."""

    def __init__(self, generator: CompetencyQuestionPort):
        super().__init__()
        self.generator = generator

    async def _execute_internal(
        self, request: GenerateCompetencyQuestionsRequest
    ) -> GenerateCompetencyQuestionsResponse:
        questions = self.generator.generate_competency_questions(
            context=request.context,
            tenant_id=request.tenant_id,
            num_questions=request.num_questions,
        )
        tagged = [
            CompetencyQuestion(id=f"CQ{idx + 1}", question=q)
            for idx, q in enumerate(questions)
        ]
        return GenerateCompetencyQuestionsResponse(competency_questions=tagged)

    def _validate_request_internal(
        self, request: GenerateCompetencyQuestionsRequest
    ) -> None:
        if not request.context.strip():
            raise ValidationError("context cannot be empty", field="context")
        if request.num_questions <= 0:
            raise ValidationError(
                "num_questions must be positive", field="num_questions"
            )

