"""Unit tests for InMemoryMessageBusAdapter."""

from unittest.mock import MagicMock, Mock

import pytest
import time
from typing import List

from adapters.inmemory_message_bus_adapter import InMemoryMessageBusAdapter
from application.ports import TracingPort


class TestInMemoryMessageBusAdapter:
    @pytest.fixture
    def bus(self) -> InMemoryMessageBusAdapter:
        return InMemoryMessageBusAdapter()

    def test_publish_and_subscribe(
        self, bus: InMemoryMessageBusAdapter
    ) -> None:  # noqa: E501
        received = []

        def handler(msg):
            received.append(msg)

        bus.subscribe(topic="test", handler=handler, tenant_id="t1")
        bus.publish(topic="test", message={"a": 1}, tenant_id="t1")

        assert received == [{"a": 1}]

    def test_idempotent_publish(self, bus: InMemoryMessageBusAdapter) -> None:
        received = []

        def handler(msg):
            received.append(msg)

        bus.subscribe(topic="dup", handler=handler, tenant_id="t1")
        bus.publish(
            topic="dup",
            message={"v": 1},
            idempotency_key="1",
            tenant_id="t1",
        )
        bus.publish(
            topic="dup",
            message={"v": 1},
            idempotency_key="1",
            tenant_id="t1",
        )

        assert len(received) == 1

    def test_tenant_isolation(self, bus: InMemoryMessageBusAdapter) -> None:
        t1_msgs = []
        t2_msgs = []
        bus.subscribe(
            topic="iso", handler=lambda m: t1_msgs.append(m), tenant_id="t1"
        )  # noqa: E501
        bus.subscribe(
            topic="iso", handler=lambda m: t2_msgs.append(m), tenant_id="t2"
        )  # noqa: E501

        bus.publish(
            topic="iso",
            message={"x": True},
            tenant_id="t1",
        )

        assert t1_msgs == [{"x": True}]
        assert t2_msgs == []

    def test_tracing_integration(self) -> None:
        tracer = Mock(spec=TracingPort)
        tracer.start_span.return_value = MagicMock()
        bus = InMemoryMessageBusAdapter(tracer=tracer)
        bus.subscribe(topic="trace", handler=lambda m: None, tenant_id="t1")
        bus.publish(topic="trace", message={}, tenant_id="t1")

        tracer.start_span.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_async_with_sync_handler(
        self, bus: InMemoryMessageBusAdapter
    ) -> None:
        received: list[dict[str, int]] = []

        def handler(msg: dict[str, int]) -> None:
            received.append(msg)

        await bus.subscribe_async(topic="a", handler=handler, tenant_id="t1")
        await bus.publish_async(topic="a", message={"v": 1}, tenant_id="t1")

        assert received == [{"v": 1}]

    @pytest.mark.asyncio
    async def test_async_methods_interoperability(
        self, bus: InMemoryMessageBusAdapter
    ) -> None:
        received: list[dict[str, int]] = []

        bus.subscribe(topic="b", handler=lambda m: received.append(m), tenant_id="t1")
        await bus.publish_async(topic="b", message={"w": 2}, tenant_id="t1")

        assert received == [{"w": 2}]
