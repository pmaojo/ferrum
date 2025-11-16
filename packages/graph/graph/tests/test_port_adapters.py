"""Tests for in-memory port adapter implementations."""

"""Tests for the simple in-memory port adapters."""

from adapters.monitoring.inmemory_metrics_adapter import InMemoryMetricsAdapter
from adapters.monitoring.inmemory_alert_adapter import InMemoryAlertAdapter
from adapters.ontology.inmemory_ontology_adapter import InMemoryOntologyAdapter
from adapters.knowledge_graph.inmemory_knowledge_graph_adapter import (
    InMemoryKnowledgeGraphAdapter,
)
from application.ports.alert_port import AlertSeverity
from domain.entities.triple import Triple


def test_inmemory_metrics_adapter_records_and_retrieves():
    adapter = InMemoryMetricsAdapter()
    adapter.record_counter("requests", 2)
    adapter.record_gauge("cpu", 0.5)
    metrics = adapter.get_metrics()
    assert any(m["name"] == "requests" and m["value"] == 2 for m in metrics)
    health = adapter.get_health_metrics()
    assert health["total_metrics"] == 2


def test_inmemory_alert_adapter_stores_alerts():
    adapter = InMemoryAlertAdapter()
    adapter.send_alert("t", "m", AlertSeverity.LOW)
    adapter.send_health_alert("db", "down", {"code": 500})
    adapter.send_performance_alert("latency", 200, 100)
    alerts = adapter.alerts["default"]
    assert len(alerts) == 3
    assert alerts[0]["title"] == "t"


def test_inmemory_ontology_adapter_basic_flow():
    adapter = InMemoryOntologyAdapter()
    assert adapter.load_base_ontology("tenant")
    triples = adapter.import_architecture_graph(
        "tenant", {"triples": [{"subject": "s", "predicate": "p", "object": "o"}]}
    )
    assert len(triples) == 1
    report = adapter.validate_architecture("tenant")
    assert report.is_consistent
    turtle = adapter.export_rdf_turtle("tenant")
    assert "s" in turtle
    react_flow = adapter.export_react_flow_format("tenant")
    assert react_flow["edges"][0]["source"] == "s"


def test_inmemory_knowledge_graph_adapter_operations():
    adapter = InMemoryKnowledgeGraphAdapter()
    triple = Triple("s", "p", "o")
    adapter.add_triple("tenant", triple)
    assert adapter.query_triples("tenant", subject="s")[0] == triple
    results = adapter.execute_sparql("tenant", "SELECT * WHERE { ?s ?p ?o }")
    assert results[0]["subject"] == "s"
    adapter.remove_triple("tenant", triple)
    assert adapter.query_triples("tenant") == []
    adapter.add_triple("tenant", triple)
    adapter.clear_graph("tenant")
    assert adapter.query_triples("tenant") == []
