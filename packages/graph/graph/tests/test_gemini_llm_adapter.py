"""Unit tests for GeminiLLMAdapter."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pytest
pytest.importorskip("redis")

from adapters.llm.gemini_llm_adapter import GeminiLLMAdapter, LLMException, QuotaExceededException


class TestGeminiLLMAdapter:
    """Test suite for GeminiLLMAdapter."""

    @patch('infrastructure.stubs.google.generativeai.configure')
    @patch('infrastructure.stubs.google.generativeai.list_models')
    def test_initialization(self, mock_list_models, mock_configure):
        """Test adapter initialization with API key validation."""
        # Arrange
        api_key = "test_api_key"
        tracer = Mock()

        # Act
        adapter = GeminiLLMAdapter(api_key=api_key, tracer=tracer)

        # Assert
        mock_configure.assert_called_once_with(api_key=api_key)
        mock_list_models.assert_called_once()
        assert adapter.generation_model == "gemini-2.5-flash"
        assert adapter.embedding_model == "text-embedding-004"

    @patch('infrastructure.stubs.google.generativeai.configure')
    @patch('infrastructure.stubs.google.generativeai.list_models')
    def test_initialization_with_custom_models(self, mock_list_models, mock_configure):
        """Test adapter initialization with custom model names."""
        # Arrange
        api_key = "test_api_key"
        generation_model = "gemini-1.5-pro"
        embedding_model = "text-embedding-005"

        # Act
        adapter = GeminiLLMAdapter(
            api_key=api_key,
            generation_model=generation_model,
            embedding_model=embedding_model
        )

        # Assert
        assert adapter.generation_model == generation_model
        assert adapter.embedding_model == embedding_model

    @patch('infrastructure.stubs.google.generativeai.configure')
    @patch('infrastructure.stubs.google.generativeai.list_models', side_effect=Exception("API Error"))
    def test_initialization_failure(self, mock_list_models, mock_configure):
        """Test adapter initialization failure with invalid API key."""
        # Arrange
        api_key = "invalid_api_key"

        # Act & Assert
        with pytest.raises(LLMException) as excinfo:
            GeminiLLMAdapter(api_key=api_key)

        assert "Failed to initialize Gemini API" in str(excinfo.value)
        assert excinfo.value.error_code == "GEMINI_API_KEY_INVALID"

    @patch('infrastructure.stubs.google.generativeai.configure')
    @patch('infrastructure.stubs.google.generativeai.list_models')
    @patch('infrastructure.stubs.google.generativeai.GenerativeModel')
    def test_generate_text(self, mock_generative_model, mock_list_models, mock_configure):
        """Test text generation with Gemini."""
        # Arrange
        api_key = "test_api_key"
        prompt = "Tell me about GraphRAG"
        tenant_id = "tenant1"
        expected_response = "GraphRAG is a framework for knowledge graph construction."

        mock_model_instance = Mock()
        mock_response = Mock()
        mock_response.text = expected_response
        mock_model_instance.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model_instance

        adapter = GeminiLLMAdapter(api_key=api_key)

        # Act
        response = adapter.generate(prompt=prompt, tenant_id=tenant_id)

        # Assert
        assert response == expected_response
        mock_model_instance.generate_content.assert_called_once_with(prompt)

    @patch('infrastructure.stubs.google.generativeai.configure')
    @patch('infrastructure.stubs.google.generativeai.list_models')
    @patch('infrastructure.stubs.google.generativeai.GenerativeModel')
    def test_generate_with_tools(self, mock_generative_model, mock_list_models, mock_configure):
        """Test text generation with function calling tools."""
        # Arrange
        api_key = "test_api_key"
        prompt = "What's the weather in Seattle?"
        tenant_id = "tenant1"
        expected_response = "The weather in Seattle is rainy."

        tools = [{
            "name": "get_weather",
            "description": "Get weather information for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    }
                },
                "required": ["location"]
            }
        }]

        mock_model_instance = Mock()
        mock_response = Mock()
        mock_response.text = expected_response
        mock_model_instance.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model_instance

        adapter = GeminiLLMAdapter(api_key=api_key)

        # Act
        response = adapter.generate(prompt=prompt, tenant_id=tenant_id, tools=tools)

        # Assert
        assert response == expected_response
        mock_model_instance.generate_content.assert_called_once()
        # Verify tools were passed (exact format is tested in _convert_tools_format)
        args, kwargs = mock_model_instance.generate_content.call_args
        assert 'tools' in kwargs

    @patch('infrastructure.stubs.google.generativeai.configure')
    @patch('infrastructure.stubs.google.generativeai.list_models')
    @patch('infrastructure.stubs.google.generativeai.get_embedding_model')
    def test_embed_text(self, mock_get_embedding_model, mock_list_models, mock_configure):
        """Test embedding generation with Gemini."""
        # Arrange
        api_key = "test_api_key"
        text = "GraphRAG knowledge graph"
        tenant_id = "tenant1"
        expected_embedding = [0.1, 0.2, 0.3, 0.4]

        mock_embedding_model = Mock()
        mock_response = Mock()
        mock_response.embedding = expected_embedding
        mock_embedding_model.embed_content.return_value = mock_response
        mock_get_embedding_model.return_value = mock_embedding_model

        adapter = GeminiLLMAdapter(api_key=api_key)

        # Act
        embedding = adapter.embed(text=text, tenant_id=tenant_id)

        # Assert
        assert embedding == expected_embedding
        mock_embedding_model.embed_content.assert_called_once_with(text)

    @patch('infrastructure.stubs.google.generativeai.configure')
    @patch('infrastructure.stubs.google.generativeai.list_models')
    @patch('infrastructure.stubs.google.generativeai.get_embedding_model')
    def test_embed_batch(self, mock_get_embedding_model, mock_list_models, mock_configure):
        """Test batch embedding generation with Gemini."""
        # Arrange
        api_key = "test_api_key"
        texts = ["GraphRAG", "Knowledge Graph", "Ontology"]
        tenant_id = "tenant1"
        expected_embeddings = [
            [0.1, 0.2],
            [0.3, 0.4],
            [0.5, 0.6]
        ]

        mock_embedding_model = Mock()
        mock_responses = [Mock(), Mock(), Mock()]
        for i, resp in enumerate(mock_responses):
            resp.embedding = expected_embeddings[i]
        mock_embedding_model.batch_embed_content.return_value = mock_responses
        mock_get_embedding_model.return_value = mock_embedding_model

        adapter = GeminiLLMAdapter(api_key=api_key)

        # Act
        embeddings = adapter.embed(text=texts, tenant_id=tenant_id)

        # Assert
        assert embeddings == expected_embeddings
        mock_embedding_model.batch_embed_content.assert_called_once_with(texts)

    @patch('infrastructure.stubs.google.generativeai.configure')
    @patch('infrastructure.stubs.google.generativeai.list_models')
    @patch('infrastructure.stubs.google.generativeai.count_tokens')
    def test_get_token_count(self, mock_count_tokens, mock_list_models, mock_configure):
        """Test token counting functionality."""
        # Arrange
        api_key = "test_api_key"
        text = "This is a test sentence for token counting."
        expected_count = 10

        mock_token_result = Mock()
        mock_token_result.total_tokens = expected_count
        mock_count_tokens.return_value = mock_token_result

        adapter = GeminiLLMAdapter(api_key=api_key)

        # Act
        token_count = adapter.get_token_count(text=text)

        # Assert
        assert token_count == expected_count
        mock_count_tokens.assert_called_once()

    @patch('infrastructure.stubs.google.generativeai.configure')
    @patch('infrastructure.stubs.google.generativeai.list_models')
    @patch('infrastructure.stubs.google.generativeai.GenerativeModel')
    def test_streaming_response(self, mock_generative_model, mock_list_models, mock_configure):
        """Test streaming response functionality."""
        # Arrange
        api_key = "test_api_key"
        prompt = "Tell me a story"
        tenant_id = "tenant1"

        # Create mock streaming response
        mock_chunks = [Mock(), Mock(), Mock()]
        mock_chunks[0].text = "Once "
        mock_chunks[1].text = "upon "
        mock_chunks[2].text = "a time"

        mock_model_instance = Mock()
        mock_model_instance.generate_content.return_value = mock_chunks
        mock_generative_model.return_value = mock_model_instance

        adapter = GeminiLLMAdapter(api_key=api_key)

        # Act
        response_stream = adapter.generate(prompt=prompt, tenant_id=tenant_id, stream=True)

        # Assert
        mock_model_instance.generate_content.assert_called_once()
        args, kwargs = mock_model_instance.generate_content.call_args
        assert kwargs.get('stream') is True

        # Since we're mocking, we check that the streaming helper exists
        assert hasattr(adapter, '_handle_streaming')

    @patch('infrastructure.stubs.google.generativeai.configure')
    @patch('infrastructure.stubs.google.generativeai.list_models')
    @patch('infrastructure.stubs.google.generativeai.GenerativeModel')
    def test_quota_exceeded_handling(self, mock_generative_model, mock_list_models, mock_configure):
        """Test handling of quota exceeded errors."""
        # Arrange
        from infrastructure.stubs.google.api_core.exceptions import ResourceExhausted

        api_key = "test_api_key"
        prompt = "Tell me about GraphRAG"
        tenant_id = "tenant1"

        mock_model_instance = Mock()
        mock_model_instance.generate_content.side_effect = ResourceExhausted("Quota exceeded")
        mock_generative_model.return_value = mock_model_instance

        adapter = GeminiLLMAdapter(api_key=api_key)

        # Act & Assert
        with pytest.raises(QuotaExceededException) as excinfo:
            adapter.generate(prompt=prompt, tenant_id=tenant_id)

        assert "Gemini API quota exceeded" in str(excinfo.value)
        assert excinfo.value.error_code == "GEMINI_QUOTA_EXCEEDED"

    @patch('infrastructure.stubs.google.generativeai.configure')
    @patch('infrastructure.stubs.google.generativeai.list_models')
    def test_convert_safety_settings(self, mock_list_models, mock_configure):
        """Test conversion of safety settings to Gemini format."""
        # Arrange
        api_key = "test_api_key"
        adapter = GeminiLLMAdapter(api_key=api_key)

        safety_settings = {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_HIGH_AND_ABOVE"
        }

        # Act
        gemini_settings = adapter._convert_safety_settings(safety_settings)

        # Assert
        assert len(gemini_settings) == 2
        # We can't directly compare enum values in the test, but we can check structure
        assert all(isinstance(setting, dict) for setting in gemini_settings)
        assert all("category" in setting and "threshold" in setting for setting in gemini_settings)

    @patch('infrastructure.stubs.google.generativeai.configure')
    @patch('infrastructure.stubs.google.generativeai.list_models')
    def test_convert_tools_format(self, mock_list_models, mock_configure):
        """Test conversion of tools to Gemini format."""
        # Arrange
        api_key = "test_api_key"
        adapter = GeminiLLMAdapter(api_key=api_key)

        tools = [{
            "name": "get_weather",
            "description": "Get weather information for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    }
                },
                "required": ["location"]
            }
        }]

        # Act
        gemini_tools = adapter._convert_tools_format(tools)

        # Assert
        assert len(gemini_tools) == 1
        assert "function_declarations" in gemini_tools[0]
        assert len(gemini_tools[0]["function_declarations"]) == 1
        assert gemini_tools[0]["function_declarations"][0]["name"] == "get_weather"
        assert "description" in gemini_tools[0]["function_declarations"][0]
        assert "parameters" in gemini_tools[0]["function_declarations"][0]

    @patch('infrastructure.stubs.google.generativeai.configure')
    @patch('infrastructure.stubs.google.generativeai.list_models')
    def test_generate_invokes_private_methods(self, mock_list_models, mock_configure):
        """Ensure generate orchestrates via private helpers."""
        api_key = "test_api_key"
        adapter = GeminiLLMAdapter(api_key=api_key)

        with patch.object(adapter, "_configure_model") as mock_config, \
             patch.object(adapter, "_record_generation_metrics") as mock_record, \
             patch.object(adapter, "_convert_safety_settings", return_value=[]):
            mock_model = Mock()
            mock_model.generate_content.return_value = Mock(text="ok")
            mock_config.return_value = mock_model

            result = adapter.generate(prompt="hello", tenant_id="tenant1")

            mock_config.assert_called_once()
            mock_record.assert_called_once()
            assert result == "ok"

    @patch('infrastructure.stubs.google.generativeai.configure')
    @patch('infrastructure.stubs.google.generativeai.list_models')
    def test_generate_streaming_uses_handle_streaming(self, mock_list_models, mock_configure):
        """Ensure streaming generation delegates to _handle_streaming."""
        api_key = "test_api_key"
        adapter = GeminiLLMAdapter(api_key=api_key)

        with patch.object(adapter, "_configure_model") as mock_config, \
             patch.object(adapter, "_handle_streaming") as mock_stream, \
             patch.object(adapter, "_convert_safety_settings", return_value=[]):
            mock_stream.return_value = iter(["token"])
            mock_model = Mock()
            mock_config.return_value = mock_model

            result = adapter.generate(prompt="hi", tenant_id="tenant1", stream=True)

            mock_stream.assert_called_once()
            assert result == mock_stream.return_value
