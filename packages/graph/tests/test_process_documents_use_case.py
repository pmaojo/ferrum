import pytest
from unittest.mock import Mock
from io import BytesIO
from PyPDF2 import PdfWriter

from application.use_cases.knowledge_graph.process_documents_use_case import (
    ProcessDocumentsUseCase,
    ProcessDocumentsRequest,
    DocumentFormat,
)
from adapters.knowledge_graph.simple_document_parser_adapter import (
    SimpleDocumentParserAdapter,
)


class TestProcessDocumentsUseCase:
    def setup_method(self):
        self.parser = SimpleDocumentParserAdapter()
        self.tracer = Mock()
        self.tracer.start_span.return_value.__enter__ = lambda s: Mock(duration_ms=0)
        self.tracer.start_span.return_value.__exit__ = lambda *a: None
        self.use_case = ProcessDocumentsUseCase(self.parser, self.tracer)

    def _make_pdf_bytes(self, text: str) -> bytes:
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        buf = BytesIO()
        writer.write(buf)
        return buf.getvalue()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_detect_and_parse_text(self):
        request = ProcessDocumentsRequest(
            documents=[b"Hello world"],
            tenant_id="t",
            user_id="u",
            format=DocumentFormat.AUTO,
        )
        response = await self.use_case.execute(request)
        assert response.success
        assert response.parsed_documents[0].strip() == "Hello world"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_parse_csv(self):
        data = b"name,age\nJohn,30\n"
        request = ProcessDocumentsRequest(
            documents=[data],
            tenant_id="t",
            user_id="u",
            format=DocumentFormat.AUTO,
        )
        response = await self.use_case.execute(request)
        assert response.success
        assert response.parsed_documents[0][0]["name"] == "John"

