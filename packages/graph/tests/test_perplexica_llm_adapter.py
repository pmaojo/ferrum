"""Unit tests for PerplexicaLLMAdapter."""

from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
pytest.importorskip("aiohttp")

from adapters.llm.perplexica_llm_adapter import PerplexicaLLMAdapter, LLMException, QuotaExceededException


class TestPerplexicaLLMAdapter:
    """Test suite for the PerplexicaLLMAdapter."""

    @patch('adapters.llm.perplexica_llm_adapter.PerplexicaClient')
    def test_initialization(self, mock_client):
        api_key = 'key'
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        adapter = PerplexicaLLMAdapter(api_key=api_key)

        mock_client.assert_called_once_with(api_key)
        mock_instance.list_models.assert_called_once()
        assert adapter.generation_model == 'perplexica-gpt'
        assert adapter.embedding_model == 'perplexica-embed'

    @patch('adapters.llm.perplexica_llm_adapter.PerplexicaClient')
    def test_generate_text(self, mock_client):
        client = Mock()
        client.generate.return_value = SimpleNamespace(text='ok')
        mock_client.return_value = client

        adapter = PerplexicaLLMAdapter(api_key='k')

        result = adapter.generate(prompt='hi', tenant_id='t')

        client.generate.assert_called_once()
        assert result == 'ok'

    @patch('adapters.llm.perplexica_llm_adapter.PerplexicaClient')
    def test_generate_streaming(self, mock_client):
        chunks = [SimpleNamespace(text='a'), SimpleNamespace(text='b')]
        client = Mock()
        client.generate.return_value = iter(chunks)
        mock_client.return_value = client

        adapter = PerplexicaLLMAdapter(api_key='k')

        result = list(adapter.generate(prompt='hi', tenant_id='t', stream=True))

        assert result == ['a', 'b']
        client.generate.assert_called_once()

    @patch('adapters.llm.perplexica_llm_adapter.PerplexicaClient')
    def test_embed_text(self, mock_client):
        client = Mock()
        client.embed.return_value = SimpleNamespace(embedding=[0.1, 0.2])
        mock_client.return_value = client

        adapter = PerplexicaLLMAdapter(api_key='k')

        emb = adapter.embed(text='txt', tenant_id='t')

        assert emb == [0.1, 0.2]
        client.embed.assert_called_once()

    @patch('adapters.llm.perplexica_llm_adapter.PerplexicaClient')
    def test_get_token_count(self, mock_client):
        client = Mock()
        client.count_tokens.return_value = SimpleNamespace(total_tokens=5)
        mock_client.return_value = client

        adapter = PerplexicaLLMAdapter(api_key='k')

        count = adapter.get_token_count(text='hello world')

        assert count == 5
        client.count_tokens.assert_called_once_with('hello world')

    @patch('adapters.llm.perplexica_llm_adapter.PerplexicaClient')
    def test_quota_exceeded(self, mock_client):
        from infrastructure.stubs.perplexica.exceptions import QuotaExceeded

        client = Mock()
        client.generate.side_effect = QuotaExceeded('limit')
        mock_client.return_value = client

        adapter = PerplexicaLLMAdapter(api_key='k')

        with pytest.raises(QuotaExceededException):
            adapter.generate(prompt='hi', tenant_id='t')

