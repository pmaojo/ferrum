import pytest
from unittest.mock import Mock
from types import SimpleNamespace
from datetime import datetime, timedelta

from domain.alert_manager import AlertManager
from application.ports import TracingPort, MessageBusPort
from domain.entities.knowledge_graph import ValidationReport


@pytest.fixture
def tracer() -> Mock:
    return Mock(spec=TracingPort)


@pytest.fixture
def message_bus() -> Mock:
    return Mock(spec=MessageBusPort)


@pytest.fixture
def alert_manager(tracer: Mock, message_bus: Mock) -> AlertManager:
    return AlertManager(
        tracer=tracer,
        message_bus=message_bus,
        alert_thresholds={"latency_p95": 100},
    )


def test_high_latency_alert(alert_manager: AlertManager, message_bus: Mock, tracer: Mock) -> None:
    alert_manager.check_performance_alerts(
        operation_name="op",
        duration_ms=150,
        success=True,
        tenant_id="t",
    )

    message_bus.publish.assert_called_once()
    alert = message_bus.publish.call_args.kwargs["message"]
    assert alert["alert_type"] == "high_latency"
    tracer.record_metric.assert_called_once()
    assert tracer.record_metric.call_args.kwargs["name"] == "alerts.high_latency"


def test_operation_failure_alert(alert_manager: AlertManager, message_bus: Mock, tracer: Mock) -> None:
    message_bus.reset_mock()
    tracer.reset_mock()

    alert_manager.check_performance_alerts(
        operation_name="op",
        duration_ms=50,
        success=False,
        tenant_id="t",
    )

    message_bus.publish.assert_called_once()
    alert = message_bus.publish.call_args.kwargs["message"]
    assert alert["alert_type"] == "operation_failure"
    tracer.record_metric.assert_called_once()
    assert tracer.record_metric.call_args.kwargs["name"] == "alerts.operation_failure"


def test_alert_cooldown(alert_manager: AlertManager, message_bus: Mock, monkeypatch: pytest.MonkeyPatch) -> None:
    now = {"value": datetime(2024, 1, 1, 0, 0, 0)}
    fake_dt = SimpleNamespace(now=lambda: now["value"])
    monkeypatch.setattr("domain.alert_manager.datetime", fake_dt)

    alert_manager.check_performance_alerts(
        operation_name="op",
        duration_ms=150,
        success=True,
        tenant_id="t",
    )
    assert message_bus.publish.call_count == 1

    now["value"] += timedelta(seconds=299)
    alert_manager.check_performance_alerts(
        operation_name="op",
        duration_ms=150,
        success=True,
        tenant_id="t",
    )
    assert message_bus.publish.call_count == 1

    now["value"] += timedelta(seconds=2)
    alert_manager.check_performance_alerts(
        operation_name="op",
        duration_ms=150,
        success=True,
        tenant_id="t",
    )
    assert message_bus.publish.call_count == 2


def test_validation_failure_alert(alert_manager: AlertManager, message_bus: Mock) -> None:
    report = ValidationReport(
        is_consistent=False,
        unsat_classes=["c1"],
        repair_suggestions=["fix"],
        tenant_id="t",
        ontology_version_id="v1",
    )

    alert_manager.trigger_validation_failure_alert(validation_report=report, tenant_id="t")

    message_bus.publish.assert_called_once()
    alert = message_bus.publish.call_args.kwargs["message"]
    assert alert["alert_type"] == "validation_failure"
