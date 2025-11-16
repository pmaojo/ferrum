import pytest
from unittest.mock import Mock

from domain.metrics_recorder import MetricsRecorder
from domain.entities import ValidationReport
from application.ports import TracingPort
from domain.alert_manager import AlertManager


def create_recorder():
    tracer = Mock(spec=TracingPort)
    alert_manager = Mock(spec=AlertManager)
    recorder = MetricsRecorder(tracer=tracer, alert_manager=alert_manager)
    return recorder, tracer, alert_manager


def test_record_operation_metrics_records_and_alerts():
    recorder, tracer, alert = create_recorder()

    recorder.record_operation_metrics(
        operation_name="query",
        duration_ms=123.0,
        success=True,
        tenant_id="t1",
        component="search",
    )

    tracer.record_metric.assert_any_call(
        name="query.duration_ms",
        value=123.0,
        tenant_id="t1",
        component="search",
    )
    tracer.record_metric.assert_any_call(
        name="query.success",
        value=1.0,
        tenant_id="t1",
        component="search",
    )
    alert.check_performance_alerts.assert_called_once_with(
        operation_name="query",
        duration_ms=123.0,
        success=True,
        tenant_id="t1",
    )


def test_record_validation_metrics_records_and_triggers_alert_on_failure():
    recorder, tracer, alert = create_recorder()
    report = ValidationReport(
        is_consistent=False,
        unsat_classes=["A", "B"],
        repair_suggestions=["fix"],
        tenant_id="t1",
        ontology_version_id="v1",
    )

    recorder.record_validation_metrics(
        validation_report=report,
        triple_count=10,
        duration_ms=50.0,
        tenant_id="t1",
    )

    tracer.record_metric.assert_any_call(
        name="validation.success",
        value=0.0,
        tenant_id="t1",
        ontology_version="v1",
    )
    tracer.record_metric.assert_any_call(
        name="validation.duration_ms",
        value=50.0,
        tenant_id="t1",
        triple_count=10,
    )
    tracer.record_metric.assert_any_call(
        name="validation.unsat_classes_count",
        value=2,
        tenant_id="t1",
    )
    tracer.record_metric.assert_any_call(
        name="validation.repair_suggestions_count",
        value=1,
        tenant_id="t1",
    )
    alert.trigger_validation_failure_alert.assert_called_once_with(
        validation_report=report, tenant_id="t1"
    )


def test_record_graph_metrics_computes_density_and_records_metrics():
    recorder, tracer, _ = create_recorder()

    recorder.record_graph_metrics(
        kg_id="kg1",
        node_count=4,
        edge_count=3,
        tenant_id="t1",
        operation="update",
    )

    tracer.record_metric.assert_any_call(
        name="graph.node_count",
        value=4,
        tenant_id="t1",
        kg_id="kg1",
        operation="update",
    )
    tracer.record_metric.assert_any_call(
        name="graph.edge_count",
        value=3,
        tenant_id="t1",
        kg_id="kg1",
        operation="update",
    )
    expected_density = 3 / (4 * 3 / 2)
    tracer.record_metric.assert_any_call(
        name="graph.density",
        value=expected_density,
        tenant_id="t1",
        kg_id="kg1",
    )
