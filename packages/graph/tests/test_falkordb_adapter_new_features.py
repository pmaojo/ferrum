import json
from unittest.mock import MagicMock, patch

import pytest
pytest.importorskip("redis")

from adapters.retrievers.falkordb_graph_adapter import FalkorGraphAdapter, FalkorDBConfig


def test_client_initialization_with_config():
    mock_manager = MagicMock()
    mock_manager.client = MagicMock()
    with patch('adapters.retrievers.falkordb_graph_adapter.FalkorDBConnectionManager', return_value=mock_manager) as manager_cls:
        config = FalkorDBConfig(host='db', port=6380, db=1, username='u', password='p', ssl=True)
        adapter = FalkorGraphAdapter(connection_config=config)
        manager_cls.assert_called_once_with(config.to_url(), pool_size=20, scripts_path=None)
        assert adapter.client is mock_manager.client


def test_back_pressure_uses_stream_check():
    mock_manager = MagicMock()
    mock_manager.client = MagicMock()
    with patch('adapters.retrievers.falkordb_graph_adapter.FalkorDBConnectionManager', return_value=mock_manager):
        adapter = FalkorGraphAdapter(connection_string='redis://localhost:6379')
    adapter.client = MagicMock()
    adapter.client.xlen.side_effect = [adapter.stream_buffer_size, adapter.stream_buffer_size - 1]
    adapter.client.xadd.return_value = '1-0'
    with patch('time.sleep') as mock_sleep:
        adapter._apply_back_pressure()
        mock_sleep.assert_called()
    adapter.client.xlen.assert_called_with(adapter.stream_key)
    adapter.client.xadd.assert_called()


def test_metadata_update_calls_lua_and_invalidate():
    mock_manager = MagicMock()
    mock_manager.client = MagicMock()
    with patch('adapters.retrievers.falkordb_graph_adapter.FalkorDBConnectionManager', return_value=mock_manager):
        adapter = FalkorGraphAdapter(connection_string='redis://localhost:6379')
    adapter._execute_lua_script = MagicMock()
    adapter._invalidate_query_cache = MagicMock()
    adapter._update_kg_metadata('kg1', 't1', 1, 2)
    adapter._execute_lua_script.assert_called_once()
    adapter._invalidate_query_cache.assert_called_once_with('kg1', 't1')


def test_cache_store_and_retrieve():
    mock_manager = MagicMock()
    mock_manager.client = MagicMock()
    with patch('adapters.retrievers.falkordb_graph_adapter.FalkorDBConnectionManager', return_value=mock_manager):
        adapter = FalkorGraphAdapter(connection_string='redis://localhost:6379')
    adapter.client = MagicMock()
    adapter.client.pipeline.return_value = MagicMock()
    adapter._cache_query_result(kg_id='kg1', tenant_id='t1', query_hash='h', params={}, result={'r': 1})
    pipe = adapter.client.pipeline.return_value
    pipe.set.assert_called_once_with('cache:query:kg1:t1:h', json.dumps({'r': 1}), ex=adapter.cache_ttl)
    pipe.sadd.assert_called_once_with('cache:index:kg1:t1', 'cache:query:kg1:t1:h')
    pipe.execute.assert_called_once()

    adapter.client.get.return_value = json.dumps({'r': 1})
    cached = adapter._check_query_cache(kg_id='kg1', tenant_id='t1', query_hash='h', params={})
    assert cached == {'r': 1}
