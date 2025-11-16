from types import SimpleNamespace

import pytest
pytest.importorskip("PIL")
pytest.importorskip("numpy")
from adapters.axiom_applier import FullAxiomApplier


class FakeOntology(SimpleNamespace):
    pass


def test_full_axiom_applier_relations():
    ontology = FakeOntology()
    axioms = [
        "Class: Person",
        "Class: Human",
        "Individual: John",
        "SubClassOf: Person Human",
        "ClassAssertion: Person John",
        "ObjectProperty: knows",
        "ObjectPropertyAssertion: knows John John",
    ]

    applier = FullAxiomApplier()
    applier.apply(ontology, axioms)

    assert hasattr(ontology, "Person")
    assert hasattr(ontology, "Human")
    assert hasattr(ontology, "John")
    assert getattr(ontology, "Person").is_a[0] is getattr(ontology, "Human")
    assert getattr(ontology, "John").is_a[0] is getattr(ontology, "Person")
    assert (getattr(ontology, "John"), getattr(ontology, "John")) in getattr(ontology, "knows").assertions
