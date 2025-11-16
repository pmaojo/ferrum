import asyncio

from application.feature_request_handler import FeatureRequestHandler
from application.use_cases.hydra.generate_personas_use_case import (
    GeneratePersonasUseCase,
)
from application.use_cases.hydra.generate_scope_document_use_case import (
    GenerateScopeDocumentUseCase,
)
from application.use_cases.hydra.generate_competency_questions_use_case import (
    GenerateCompetencyQuestionsUseCase,
)
from application.ports.hydra import (
    PersonaGeneratorPort,
    ScopeGeneratorPort,
    CompetencyQuestionPort,
)
from permagraph.repository import InMemoryGraphRepository


class DummyPersonaGenerator(PersonaGeneratorPort):
    def generate_personas(self, *, description: str, tenant_id: str, num_personas: int = 3, opts=None):
        return ["Persona A", "Persona B"]


class DummyScopeGenerator(ScopeGeneratorPort):
    def generate_scope_document(self, *, description: str, tenant_id: str, opts=None) -> str:
        return "Scope Document"


class DummyCQGenerator(CompetencyQuestionPort):
    def generate_competency_questions(self, *, context: str, tenant_id: str, num_questions: int = 10, opts=None):
        return ["What is A?", "What is B?"]


def test_feature_request_handler_persists_nodes():
    persona_uc = GeneratePersonasUseCase(DummyPersonaGenerator())
    scope_uc = GenerateScopeDocumentUseCase(DummyScopeGenerator())
    cq_uc = GenerateCompetencyQuestionsUseCase(DummyCQGenerator())
    repo = InMemoryGraphRepository()
    handler = FeatureRequestHandler(
        persona_uc=persona_uc, scope_uc=scope_uc, cq_uc=cq_uc, graph_repository=repo
    )

    result = asyncio.run(handler.handle(description="Add dark mode", tenant_id="t1"))

    assert result.feature_request.description == "Add dark mode"
    assert result.scope_document.content == "Scope Document"
    assert [p.content for p in result.personas] == ["Persona A", "Persona B"]
    assert [q.question for q in result.clarifying_questions] == [
        "What is A?",
        "What is B?",
    ]
    assert repo.get_edges()  # edges should be recorded
