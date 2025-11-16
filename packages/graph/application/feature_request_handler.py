from __future__ import annotations

"""Handler orchestrating HyDRA persona, scope and CQ generation."""

import logging
import uuid
from dataclasses import dataclass
from typing import List

from application.use_cases.hydra.generate_personas_use_case import (
    GeneratePersonasRequest,
    GeneratePersonasResponse,
    GeneratePersonasUseCase,
)
from application.use_cases.hydra.generate_scope_document_use_case import (
    GenerateScopeDocumentRequest,
    GenerateScopeDocumentResponse,
    GenerateScopeDocumentUseCase,
)
from application.use_cases.hydra.generate_competency_questions_use_case import (
    GenerateCompetencyQuestionsRequest,
    GenerateCompetencyQuestionsResponse,
    GenerateCompetencyQuestionsUseCase,
)
from permagraph.domain import (
    ClarifyingQuestion,
    FeatureRequest,
    Graph,
    Persona,
    ScopeDocument,
)
from permagraph.repository import GraphRepository


logger = logging.getLogger(__name__)


@dataclass
class FeatureRequestResult:
    """Aggregated result for processing a feature request."""

    feature_request: FeatureRequest
    scope_document: ScopeDocument
    personas: List[Persona]
    clarifying_questions: List[ClarifyingQuestion]


class FeatureRequestHandler:
    """Handle raw feature requests using HyDRA pipelines."""

    def __init__(
        self,
        *,
        persona_uc: GeneratePersonasUseCase,
        scope_uc: GenerateScopeDocumentUseCase,
        cq_uc: GenerateCompetencyQuestionsUseCase,
        graph_repository: GraphRepository,
    ) -> None:
        self._persona_uc = persona_uc
        self._scope_uc = scope_uc
        self._cq_uc = cq_uc
        self._graph = Graph(graph_repository)

    def _remove_nodes(self, *node_ids: str) -> None:
        """Remove nodes and associated edges from the graph."""
        for node_id in node_ids:
            self._graph.feature_requests.pop(node_id, None)
            self._graph.scope_documents.pop(node_id, None)
            self._graph.personas.pop(node_id, None)
            self._graph.clarifying_questions.pop(node_id, None)
            self._graph.edges = [
                e
                for e in self._graph.edges
                if e.source != node_id and e.target != node_id
            ]

    async def handle(self, *, description: str, tenant_id: str) -> FeatureRequestResult:
        """Process the feature request and persist generated artifacts."""

        fr_id = str(uuid.uuid4())
        feature_request = FeatureRequest(id=fr_id, description=description)
        self._graph.add_feature_request(feature_request)

        try:
            logger.info(
                "Generating scope document for tenant %s feature request %s",
                tenant_id,
                fr_id,
            )
            scope_resp: GenerateScopeDocumentResponse = await self._scope_uc.execute(
                GenerateScopeDocumentRequest(description=description, tenant_id=tenant_id)
            )
            scope_doc = ScopeDocument(
                id=str(uuid.uuid4()),
                content=scope_resp.scope_document,
                feature_request_id=fr_id,
            )
            self._graph.add_scope_document(scope_doc)
            logger.info(
                "Generated scope document %s for tenant %s feature request %s",
                scope_doc.id,
                tenant_id,
                fr_id,
            )
        except Exception:  # pragma: no cover - defensive rollback
            self._remove_nodes(fr_id)
            logger.exception(
                "Failed to generate scope document for tenant %s feature request %s",
                tenant_id,
                fr_id,
            )
            raise

        personas: List[Persona] = []
        try:
            logger.info(
                "Generating personas for tenant %s feature request %s",
                tenant_id,
                fr_id,
            )
            persona_resp: GeneratePersonasResponse = await self._persona_uc.execute(
                GeneratePersonasRequest(description=description, tenant_id=tenant_id)
            )
            for persona_text in persona_resp.personas:
                persona = Persona(
                    id=str(uuid.uuid4()),
                    content=persona_text,
                    feature_request_id=fr_id,
                )
                self._graph.add_persona(persona)
                personas.append(persona)
            logger.info(
                "Generated %d personas for tenant %s feature request %s",
                len(personas),
                tenant_id,
                fr_id,
            )
        except Exception:
            ids = [p.id for p in personas] + [scope_doc.id, fr_id]
            self._remove_nodes(*ids)
            logger.exception(
                "Failed to generate personas for tenant %s feature request %s",
                tenant_id,
                fr_id,
            )
            raise

        clarifying_questions: List[ClarifyingQuestion] = []
        try:
            logger.info(
                "Generating clarifying questions for tenant %s feature request %s",
                tenant_id,
                fr_id,
            )
            cq_resp: GenerateCompetencyQuestionsResponse = await self._cq_uc.execute(
                GenerateCompetencyQuestionsRequest(
                    context=description, tenant_id=tenant_id
                )
            )
            for cq in cq_resp.competency_questions:
                question = ClarifyingQuestion(
                    id=str(uuid.uuid4()),
                    question=cq.question,
                    feature_request_id=fr_id,
                )
                self._graph.add_clarifying_question(question)
                clarifying_questions.append(question)
            logger.info(
                "Generated %d clarifying questions for tenant %s feature request %s",
                len(clarifying_questions),
                tenant_id,
                fr_id,
            )
        except Exception:
            ids = [q.id for q in clarifying_questions] + [p.id for p in personas]
            ids.extend([scope_doc.id, fr_id])
            self._remove_nodes(*ids)
            logger.exception(
                "Failed to generate clarifying questions for tenant %s feature request %s",
                tenant_id,
                fr_id,
            )
            raise

        return FeatureRequestResult(
            feature_request=feature_request,
            scope_document=scope_doc,
            personas=personas,
            clarifying_questions=clarifying_questions,
        )
