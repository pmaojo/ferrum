from unittest.mock import Mock

from domain.owl_modeling_assistant import OwlModelingAssistant
from domain.entities import Triple, ValidationReport
from application.ports import OwlAxiomGeneratorPort, OntologyValidatorPort


def test_assistant_generates_and_validates():
    generator = Mock(spec=OwlAxiomGeneratorPort)
    validator = Mock(spec=OntologyValidatorPort)

    generator.generate_axioms.return_value = [
        "Class: Person",
        "ClassAssertion: Person Alice",
        "ObjectPropertyAssertion: knows Alice Bob",
    ]

    expected_triples = [
        Triple("Person", "rdf:type", "Class", "t"),
        Triple("Alice", "type", "Person", "t"),
        Triple("Alice", "knows", "Bob", "t"),
    ]

    validator.validate.return_value = ValidationReport(
        is_consistent=True,
        unsat_classes=[],
        repair_suggestions=[],
        tenant_id="t",
        ontology_version_id="v1",
    )

    assistant = OwlModelingAssistant(generator, validator)
    report = assistant.generate_model(text="x", ontology_version_id="v1", tenant_id="t")

    generator.generate_axioms.assert_called_once_with(text="x", tenant_id="t")
    validator.validate.assert_called_once()
    assert validator.validate.call_args.kwargs["triples"] == expected_triples
    assert report.is_consistent

