from unittest.mock import MagicMock, patch

from adapters.retrievers.graphrag_adapter import GraphRAGAdapter


def test_index_delegates_to_sdk():
    with patch("adapters.graphrag_adapter.GraphRAGSDKAdapter") as MockSDK:
        sdk = MockSDK.return_value
        adapter = GraphRAGAdapter()
        adapter.index(docs=["doc"], kg_id="kg", tenant_id="t")
        sdk.index.assert_called_once_with(docs=["doc"], kg_id="kg", tenant_id="t")


def test_run_delegates_to_sdk():
    with patch("adapters.graphrag_adapter.GraphRAGSDKAdapter") as MockSDK:
        sdk = MockSDK.return_value
        adapter = GraphRAGAdapter()
        adapter.run(question="q", kg_id="kg", tenant_id="t", opts=None)
        sdk.run.assert_called_once_with(question="q", kg_id="kg", tenant_id="t", opts=None)


def test_translate_delegates_to_sdk():
    with patch("adapters.graphrag_adapter.GraphRAGSDKAdapter") as MockSDK:
        sdk = MockSDK.return_value
        adapter = GraphRAGAdapter()
        adapter.translate(natural_language="hi", kg_id="kg", tenant_id="t")
        sdk.translate.assert_called_once_with(
            natural_language="hi", kg_id="kg", tenant_id="t", target_format="cypher"
        )

