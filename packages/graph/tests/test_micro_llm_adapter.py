import sys
import types
import unittest
from unittest.mock import patch, Mock
import pytest
np = pytest.importorskip("numpy")

# Stub external dependencies before importing the adapter
sys.modules['transformers'] = types.ModuleType('transformers')
sys.modules['transformers'].AutoTokenizer = Mock()
sys.modules['transformers'].AutoModelForCausalLM = Mock()
sys.modules['transformers'].pipeline = Mock()
sys.modules['sentence_transformers'] = types.ModuleType('sentence_transformers')
sys.modules['sentence_transformers'].SentenceTransformer = Mock()

from adapters.llm.micro_llm_adapter import MicroLLMAdapter, MicroLLMConfig


class TestMicroLLMAdapter(unittest.TestCase):
    """Tests for MicroLLMAdapter."""

    @patch('sentence_transformers.SentenceTransformer')
    @patch('transformers.AutoTokenizer')
    @patch('transformers.AutoModelForCausalLM')
    @patch('transformers.pipeline')
    def test_generate_text(self, mock_pipeline, mock_model, mock_tokenizer, mock_st):
        mock_pipeline.return_value = lambda *args, **kwargs: [{"generated_text": "hi"}]
        mock_st.return_value = Mock()
        mock_tokenizer.from_pretrained.return_value = Mock()
        mock_model.from_pretrained.return_value = Mock()

        adapter = MicroLLMAdapter(config=MicroLLMConfig())
        result = adapter.generate(prompt="hello", tenant_id="t1")

        self.assertEqual(result, "hi")
        mock_pipeline.assert_called_once()

    @patch('sentence_transformers.SentenceTransformer')
    @patch('transformers.AutoTokenizer')
    @patch('transformers.AutoModelForCausalLM')
    @patch('transformers.pipeline')
    def test_embed_text(self, mock_pipeline, mock_model, mock_tokenizer, mock_st):
        embedder = Mock()
        embedder.encode.return_value = [np.array([1.0, 2.0])]
        mock_st.return_value = embedder
        mock_pipeline.return_value = lambda *args, **kwargs: [{"generated_text": "hi"}]
        mock_tokenizer.from_pretrained.return_value = Mock()
        mock_model.from_pretrained.return_value = Mock()

        adapter = MicroLLMAdapter(config=MicroLLMConfig())
        result = adapter.embed(text="hello", tenant_id="t1")

        self.assertEqual(result, [1.0, 2.0])
        embedder.encode.assert_called_once()

    @patch('sentence_transformers.SentenceTransformer')
    @patch('transformers.AutoTokenizer')
    @patch('transformers.AutoModelForCausalLM')
    @patch('transformers.pipeline')
    def test_get_token_count(self, mock_pipeline, mock_model, mock_tokenizer, mock_st):
        tokenizer = Mock()
        tokenizer.encode.return_value = [1, 2, 3]
        mock_tokenizer.from_pretrained.return_value = tokenizer
        mock_model.from_pretrained.return_value = Mock()
        mock_pipeline.return_value = lambda *args, **kwargs: [{"generated_text": "hi"}]
        mock_st.return_value = Mock()

        adapter = MicroLLMAdapter(config=MicroLLMConfig())
        count = adapter.get_token_count(text="hello")

        self.assertEqual(count, 3)
        tokenizer.encode.assert_called_once_with("hello")


