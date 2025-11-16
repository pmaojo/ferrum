"""Tests for ContractValidatorAdapter."""

from adapters.knowledge_graph.contract_validator_adapter import (
    ContractValidatorAdapter,
)
from application.contracts import (
    CONNECTIVITY_RULE,
    CLASS_INSTANCE_SEPARATION_RULE,
)


def test_connectivity_rule_passes():
    adapter = ContractValidatorAdapter(
        triples=[("a", "p", "b"), ("b", "p", "c")]
    )
    valid, details = adapter.validate(
        kg_id="kg", tenant_id="t", rules=[CONNECTIVITY_RULE]
    )
    assert valid is True
    assert details[0]["status"] is True


def test_class_instance_separation_detects_violation():
    triples = [("x", "rdf:type", "owl:Class"), ("x", "rdf:type", "Person")]
    adapter = ContractValidatorAdapter(triples=triples)
    valid, details = adapter.validate(
        kg_id="kg", tenant_id="t", rules=[CLASS_INSTANCE_SEPARATION_RULE]
    )
    assert valid is False
    assert details[0]["violations"] == ["x"]
