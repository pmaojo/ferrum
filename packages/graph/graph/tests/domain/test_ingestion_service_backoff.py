import logging
from unittest.mock import Mock, patch, call

import pytest

from application.ports import GraphRetrieverPort, OntologyValidatorPort
from domain.services import IngestionService


@pytest.fixture
def ingestion_service() -> IngestionService:
    retriever = Mock(spec=GraphRetrieverPort)
    validator = Mock(spec=OntologyValidatorPort)
    return IngestionService(
        retriever=retriever,
        validator=validator,
        tracer=None,
        logger=logging.getLogger("test.ingestion.backoff"),
    )


def test_extraction_backoff_delays(ingestion_service: IngestionService) -> None:
    ingestion_service.retriever.index.side_effect = [
        Exception("fail1"),
        Exception("fail2"),
        [],
    ]
    with patch("domain.ingestion_service.time.sleep") as mock_sleep:
        ingestion_service._extract_triples_with_retry(
            doc_contents=["d"], kg_id="kg", tenant_id="t", max_retries=2
        )
    mock_sleep.assert_has_calls([call(1), call(2)])
    assert mock_sleep.call_count == 2
