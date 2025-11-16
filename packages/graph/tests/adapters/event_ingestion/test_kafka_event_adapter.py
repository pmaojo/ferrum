import importlib.util
import sys
from pathlib import Path

import pytest
from unittest.mock import AsyncMock, Mock

MODULE_PATH = (
    Path(__file__).parents[3]
    / "adapters"
    / "event_ingestion"
    / "kafka_event_adapter.py"
)
spec = importlib.util.spec_from_file_location("kafka_event_adapter", MODULE_PATH)
kafka_event_adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = kafka_event_adapter
spec.loader.exec_module(kafka_event_adapter)
KafkaEventAdapter = kafka_event_adapter.KafkaEventAdapter


@pytest.fixture
def tracer():
    tracer = Mock()
    tracer.record_metric = Mock()
    return tracer


@pytest.fixture
def context_manager():
    cm = AsyncMock()
    cm.process_advertising_event = AsyncMock()
    cm.process_ecommerce_event = AsyncMock()
    return cm


@pytest.mark.asyncio
async def test_invalid_ad_event_deadlettered(context_manager, tracer, monkeypatch):
    adapter = KafkaEventAdapter(context_manager, tracer)
    mock_producer = Mock()
    monkeypatch.setattr(adapter, "_get_producer", lambda: mock_producer)

    # Missing creative_id triggers validation failure
    invalid_event = {
        "event_type": "advertising.impression",
        "tenant_id": "t1",
        "customer_id": "c1",
        "campaign_id": "cmp1",
    }

    await adapter._process_event("advertising.impression", invalid_event)

    tracer.record_metric.assert_any_call(
        "invalid_events", 1, tenant_id="t1", event_type="advertising.impression"
    )
    mock_producer.send.assert_called_once_with("advertising.deadletter", invalid_event)
    tracer.record_metric.assert_any_call(
        "deadlettered_events", 1, tenant_id="t1", event_type="advertising.impression"
    )
    context_manager.process_advertising_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_ecommerce_event_no_deadletter(context_manager, tracer, monkeypatch):
    adapter = KafkaEventAdapter(context_manager, tracer)
    mock_producer = Mock()
    monkeypatch.setattr(adapter, "_get_producer", lambda: mock_producer)

    # Missing product_id triggers validation failure
    invalid_event = {
        "event_type": "ecommerce.product.view",
        "tenant_id": "t1",
        "customer_id": "c1",
    }

    await adapter._process_event("ecommerce.product.view", invalid_event)

    tracer.record_metric.assert_any_call(
        "invalid_events", 1, tenant_id="t1", event_type="ecommerce.product.view"
    )
    mock_producer.send.assert_not_called()
    context_manager.process_ecommerce_event.assert_not_awaited()
