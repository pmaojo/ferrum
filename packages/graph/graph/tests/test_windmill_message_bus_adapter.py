import importlib.util
from pathlib import Path

import pytest

from domain.exceptions import SubscriptionError


def load_adapter_class():
    module_path = Path(__file__).resolve().parents[1] / "adapters" / "windmill_message_bus_adapter.py"
    spec = importlib.util.spec_from_file_location("windmill_message_bus_adapter", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.WindmillMessageBusAdapter


def test_subscribe_raises_error():
    Adapter = load_adapter_class()
    adapter = Adapter(base_url="http://windmill", api_key="key")
    with pytest.raises(SubscriptionError) as exc_info:
        adapter.subscribe(topic="t", handler=lambda m: None, tenant_id="tenant")
    assert "does not support subscriptions" in str(exc_info.value)
