"""Unit tests for TinkerPopAdapter."""

from unittest.mock import Mock

import pytest
pytest.importorskip("gremlin_python")

from adapters.retrievers.tinkerpop_adapter import TinkerPopAdapter
from adapters.retrievers.tinkerpop_client import GraphDBClient


class TestTinkerPopAdapter:
    @pytest.fixture
    def mock_client(self) -> Mock:
        client = Mock(spec=GraphDBClient)
        client.query.return_value = [{"v": 1}]
        return client

    @pytest.fixture
    def adapter(self, mock_client: Mock) -> TinkerPopAdapter:
        return TinkerPopAdapter(
            endpoint="ws://localhost:8182/gremlin",
            client_factory=lambda endpoint: mock_client,
        )

    def test_execute_traversal(self, adapter: TinkerPopAdapter, mock_client: Mock) -> None:
        result = adapter.execute_traversal("g.V().limit(1)")

        mock_client.query.assert_called_once_with("g.V().limit(1)")
        assert result == [{"v": 1}]

    def test_close_closes_client(self, adapter: TinkerPopAdapter, mock_client: Mock) -> None:
        adapter.close()

        mock_client.close.assert_called_once()
