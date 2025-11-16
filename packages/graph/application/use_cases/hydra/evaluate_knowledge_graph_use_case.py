"""Use case for evaluating a knowledge graph against competency questions."""

from dataclasses import dataclass
from typing import Callable, List, Sequence

from application.exceptions import ValidationError
from application.ports.hydra import CQToQueryPort
from application.use_cases.base_use_case import BaseUseCase


@dataclass
class CompetencyQuestionEvaluation:
    """Stored competency question with expected answer."""

    id: str
    question: str
    expected_answer: Sequence[str]


@dataclass
class EvaluateKnowledgeGraphRequest:
    """Input for knowledge graph evaluation."""

    kg_id: str
    tenant_id: str
    backend: str  # "neo4j" or "sparql"
    competency_questions: List[CompetencyQuestionEvaluation]


@dataclass
class EvaluationResult:
    """Result of executing a competency question."""

    cq_id: str
    query: str
    expected: Sequence[str]
    actual: Sequence[str]
    correct: bool


@dataclass
class EvaluationSummary:
    """Aggregated evaluation metrics."""

    total_questions: int
    correct_answers: int
    accuracy: float


@dataclass
class EvaluateKnowledgeGraphResponse:
    """Output of knowledge graph evaluation."""

    results: List[EvaluationResult]
    summary: EvaluationSummary


class EvaluateKnowledgeGraphUseCase(
    BaseUseCase[EvaluateKnowledgeGraphRequest, EvaluateKnowledgeGraphResponse]
):
    """Map competency questions to queries and evaluate answers."""

    def __init__(
        self,
        *,
        neo4j_translator: CQToQueryPort,
        neo4j_runner: Callable[[str, str, str], Sequence[str]],
        sparql_translator: CQToQueryPort,
        sparql_runner: Callable[[str, str, str], Sequence[str]],
    ) -> None:
        super().__init__()
        self._neo4j_translator = neo4j_translator
        self._neo4j_runner = neo4j_runner
        self._sparql_translator = sparql_translator
        self._sparql_runner = sparql_runner

    async def _execute_internal(
        self, request: EvaluateKnowledgeGraphRequest
    ) -> EvaluateKnowledgeGraphResponse:
        translator, runner = self._select_backend(request.backend)
        results: List[EvaluationResult] = []
        correct = 0

        for cq in request.competency_questions:
            query = translator.to_query(question=cq.question)
            actual = list(runner(query, request.kg_id, request.tenant_id))
            is_correct = set(map(str, actual)) == set(map(str, cq.expected_answer))
            if is_correct:
                correct += 1
            results.append(
                EvaluationResult(
                    cq_id=cq.id,
                    query=query,
                    expected=list(cq.expected_answer),
                    actual=actual,
                    correct=is_correct,
                )
            )

        total = len(request.competency_questions)
        summary = EvaluationSummary(
            total_questions=total,
            correct_answers=correct,
            accuracy=correct / total if total else 0.0,
        )
        return EvaluateKnowledgeGraphResponse(results=results, summary=summary)

    def _select_backend(
        self, backend: str
    ) -> tuple[CQToQueryPort, Callable[[str, str, str], Sequence[str]]]:
        if backend == "neo4j":
            return self._neo4j_translator, self._neo4j_runner
        if backend == "sparql":
            return self._sparql_translator, self._sparql_runner
        raise ValidationError("Unsupported backend", field="backend")

    def _validate_request_internal(
        self, request: EvaluateKnowledgeGraphRequest
    ) -> None:
        if request.backend not in {"neo4j", "sparql"}:
            raise ValidationError(
                "backend must be 'neo4j' or 'sparql'", field="backend"
            )
        if not request.competency_questions:
            raise ValidationError(
                "competency_questions cannot be empty", field="competency_questions"
            )
        for cq in request.competency_questions:
            if not cq.question.strip():
                raise ValidationError(
                    "competency question cannot be empty", field="question"
                )
