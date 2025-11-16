"""Hybrid reasoning services combining LLM outputs with ontology validation.

This module implements lightweight services that bridge language model
responses with OWL-based reasoning.  It provides utilities for loading
ontologies, checking consistency, generating explanations, linking entities,
and orchestrating hybrid reasoning logic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from application.ports import (
    OntologyValidatorPort,
    LLMPort,
)
from application.ports.hybrid_reasoning import (
    OntologyLoaderPort,
    ConsistencyCheckerPort,
    ReasoningExplanationPort,
    EntityLinkingPort,
    HybridReasoningPort,
)
from domain.entities import Triple, ValidationReport

try:
    from owlready2 import World
except Exception:  # pragma: no cover - optional dependency
    World = object  # type: ignore


class OntologyLoaderService(OntologyLoaderPort):
    """Simple ontology loader using owlready2."""

    def __init__(self, world: Optional[Any] = None) -> None:
        self._world = world or World()

    def load(self, *, path: str) -> Any:
        return self._world.get_ontology(path).load()


class ConsistencyCheckerService(ConsistencyCheckerPort):
    """Delegates consistency checking to an OntologyValidatorPort."""

    def __init__(self, validator: OntologyValidatorPort) -> None:
        self._validator = validator

    def check(
        self, *, triples: List[Triple], ontology_version_id: str
    ) -> ValidationReport:
        return self._validator.validate(
            triples=triples, ontology_version_id=ontology_version_id
        )


class ReasoningExplanationService(ReasoningExplanationPort):
    """Generate explanations using an LLM."""

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def explain(
        self, *, report: ValidationReport, llm_output: str, tenant_id: str
    ) -> str:
        status = "consistent" if report.is_consistent else "inconsistent"
        prompt = (
            f"The ontology is {status}. "
            f"LLM answer: {llm_output}. Provide an explanation."
        )
        return self._llm.generate(prompt=prompt, tenant_id=tenant_id)


class EntityLinkingService(EntityLinkingPort):
    """Link entities using an LLM."""

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def link(self, *, text: str, ontology: Any, tenant_id: str) -> List[str]:
        iri = getattr(ontology, "base_iri", "ontology")
        prompt = f"Link entities in '{text}' to concepts in {iri}."
        result = self._llm.generate(prompt=prompt, tenant_id=tenant_id)
        return [r.strip() for r in result.split("\n") if r.strip()]


class HybridReasoningService(HybridReasoningPort):
    """Combine LLM reasoning with OWL reasoning."""

    def __init__(
        self,
        llm: LLMPort,
        validator: OntologyValidatorPort,
        explainer: ReasoningExplanationPort,
    ) -> None:
        self._llm = llm
        self._validator = validator
        self._explainer = explainer

    def reason(
        self,
        *,
        question: str,
        triples: List[Triple],
        ontology_version_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        llm_answer = self._llm.generate(prompt=question, tenant_id=tenant_id)
        report = self._validator.validate(
            triples=triples, ontology_version_id=ontology_version_id
        )
        explanation = self._explainer.explain(
            report=report, llm_output=llm_answer, tenant_id=tenant_id
        )
        return {
            "answer": llm_answer,
            "is_consistent": report.is_consistent,
            "explanation": explanation,
        }


__all__ = [
    "OntologyLoaderService",
    "ConsistencyCheckerService",
    "ReasoningExplanationService",
    "EntityLinkingService",
    "HybridReasoningService",
]
