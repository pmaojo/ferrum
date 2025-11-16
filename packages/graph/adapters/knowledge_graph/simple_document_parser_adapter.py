from __future__ import annotations

import csv
import io
import json
from typing import Any

from PyPDF2 import PdfReader

from application.use_cases.knowledge_graph.process_documents_use_case import (
    DocumentFormat,
    DocumentParserPort,
)


class SimpleDocumentParserAdapter(DocumentParserPort):
    """Basic implementation of ``DocumentParserPort`` using common libraries."""

    def detect_format(self, data: bytes) -> DocumentFormat:
        if data.startswith(b"%PDF"):
            return DocumentFormat.PDF
        try:
            json.loads(data.decode("utf-8"))
            return DocumentFormat.JSON
        except Exception:
            pass
        if b"," in data and b"\n" in data:
            return DocumentFormat.CSV
        return DocumentFormat.TEXT

    def parse_pdf(self, data: bytes) -> str:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def parse_text(self, data: bytes) -> str:
        return data.decode("utf-8", errors="ignore")

    def parse_structured(self, data: bytes, *, format: DocumentFormat) -> Any:
        text = data.decode("utf-8", errors="ignore")
        if format == DocumentFormat.JSON:
            return json.loads(text)
        elif format == DocumentFormat.CSV:
            reader = csv.DictReader(io.StringIO(text))
            return [row for row in reader]
        else:  # pragma: no cover - should not happen
            return text
