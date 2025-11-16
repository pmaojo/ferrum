from __future__ import annotations

from typing import List, Set

from domain.entities import Triple


def _normalize_entity_name(name: str) -> str:
    """Normalize entity name for Manchester syntax."""
    import re

    normalized = re.sub(r"[^\w]", "_", name)
    if normalized and not normalized[0].isalpha():
        normalized = "e_" + normalized
    return normalized


def _is_data_property(value: str) -> bool:
    """Return True if value looks like a literal."""
    return (
        (value.startswith('"') and value.endswith('"'))
        or (value.startswith("'") and value.endswith("'"))
        or value.replace(".", "", 1).isdigit()
    )


def convert_triples_to_owl(triples: List[Triple]) -> str:
    """Convert triples to OWL Manchester syntax."""
    manchester = "Ontology: <http://example.org/ontology>\n\n"
    classes: Set[str] = set()
    object_properties: Set[str] = set()
    data_properties: Set[str] = set()
    individuals: Set[str] = set()

    for triple in triples:
        subject = _normalize_entity_name(triple.subject)
        predicate = _normalize_entity_name(triple.predicate)
        obj = _normalize_entity_name(triple.object)
        is_data = _is_data_property(triple.object)

        if predicate.lower() in {"type", "rdf:type"}:
            classes.add(obj)
            individuals.add(subject)
        else:
            individuals.add(subject)
            individuals.add(obj)
            if is_data:
                data_properties.add(predicate)
            else:
                object_properties.add(predicate)

    if classes:
        manchester += "Class: " + "\n\nClass: ".join(classes) + "\n\n"
    if object_properties:
        manchester += (
            "ObjectProperty: " + "\n\nObjectProperty: ".join(object_properties) + "\n\n"
        )
    if data_properties:
        manchester += (
            "DataProperty: " + "\n\nDataProperty: ".join(data_properties) + "\n\n"
        )
    if individuals:
        manchester += "Individual: " + "\n\nIndividual: ".join(individuals) + "\n\n"

    for triple in triples:
        subject = _normalize_entity_name(triple.subject)
        predicate = _normalize_entity_name(triple.predicate)
        obj = _normalize_entity_name(triple.object)
        is_data = _is_data_property(triple.object)
        if predicate.lower() in {"type", "rdf:type"}:
            manchester += f"ClassAssertion: {obj} {subject}\n"
        elif is_data:
            manchester += f"DataPropertyAssertion: {predicate} {subject} {obj}\n"
        else:
            manchester += f"ObjectPropertyAssertion: {predicate} {subject} {obj}\n"

    return manchester
