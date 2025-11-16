from domain.entities import Triple
from domain.owl_conversion import (
    convert_triples_to_owl,
    _normalize_entity_name,
    _is_data_property,
)


def test_convert_triples_to_owl():
    triples = [
        Triple("Person1", "type", "Person", "t1"),
        Triple("Person1", "knows", "Person2", "t1"),
        Triple("Person1", "age", "30", "t1"),
    ]
    owl = convert_triples_to_owl(triples)
    assert "Class: Person" in owl
    assert "Individual: Person1" in owl
    assert "ObjectPropertyAssertion: knows Person1 Person2" in owl
    assert "DataPropertyAssertion: age Person1 e_30" in owl


def test_utils():
    assert _normalize_entity_name("John Doe") == "John_Doe"
    assert _normalize_entity_name("123") == "e_123"
    assert _is_data_property("42")
    assert not _is_data_property("Entity")
