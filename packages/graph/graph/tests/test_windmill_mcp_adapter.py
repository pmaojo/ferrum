import json
from unittest.mock import MagicMock, patch

import pytest

from adapters.windmill_mcp_adapter import WindmillMCPAdapter


class MockResponse:
    def __init__(self, lines):
        self.lines = lines

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def iter_lines(self):
        for line in self.lines:
            yield line

    def raise_for_status(self):
        pass


@pytest.fixture
def mock_client():
    return MagicMock()


def test_publish_sends_http_request(mock_client):
    adapter = WindmillMCPAdapter(base_url="http://mcp", http_client=mock_client)
    adapter.publish(topic="t", message={"a": 1}, tenant_id="tenant")

    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert args[0] == "http://mcp/publish"
    assert kwargs["json"]["topic"] == "t"
    assert kwargs["json"]["tenant_id"] == "tenant"


def test_subscribe_processes_events(mock_client):
    event = json.dumps({"x": 1}).encode()
    mock_client.stream.return_value = MockResponse([event])

    adapter = WindmillMCPAdapter(base_url="http://mcp", http_client=mock_client)

    received = []

    with patch("threading.Thread") as MockThread:
        def fake_thread(*args, **kwargs):
            thread = MagicMock()
            target = kwargs.get("target")
            kw = kwargs.get("kwargs", {})
            thread.start.side_effect = lambda: target(**kw)
            return thread

        MockThread.side_effect = fake_thread

        adapter.subscribe(topic="t", handler=lambda m: received.append(m), tenant_id="tenant")

    assert received == [{"x": 1}]
