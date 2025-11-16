import unittest
from unittest.mock import MagicMock

from domain.hybrid_reasoning import (
    HybridReasoningService,
    ReasoningExplanationService,
)
from application.ports import LLMPort, OntologyValidatorPort
from domain.entities import Triple, ValidationReport


class TestHybridReasoningService(unittest.TestCase):
    def setUp(self):
        self.llm = MagicMock(spec=LLMPort)
        self.validator = MagicMock(spec=OntologyValidatorPort)
        self.validator.validate.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id="t1",
            ontology_version_id="v1",
        )
        self.explainer = ReasoningExplanationService(self.llm)
        self.service = HybridReasoningService(self.llm, self.validator, self.explainer)
        self.sample_triple = Triple("a", "b", "c", "t1")

    def test_reason_invokes_llm_and_validator(self):
        self.llm.generate.return_value = "Answer"

        result = self.service.reason(
            question="Q", triples=[self.sample_triple], ontology_version_id="v1", tenant_id="t1"
        )

        self.llm.generate.assert_called()
        self.validator.validate.assert_called_once()
        assert result["answer"] == "Answer"
        assert result["is_consistent"] is True
        assert "explanation" in result


if __name__ == "__main__":
    unittest.main()
