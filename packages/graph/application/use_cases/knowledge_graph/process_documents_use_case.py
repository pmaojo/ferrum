from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Protocol

from application.exceptions import ApplicationError, ValidationError
from application.ports import TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, TenantScopedRequestDTO


class DocumentFormat(str, Enum):
    """Supported document formats."""

    AUTO = "auto"
    PDF = "pdf"
    TEXT = "text"
    JSON = "json"
    CSV = "csv"


class DocumentParserPort(Protocol):
    """Port for parsing different document formats."""

    def detect_format(self, data: bytes) -> DocumentFormat: ...

    def parse_pdf(self, data: bytes) -> str: ...

    def parse_text(self, data: bytes) -> str: ...

    def parse_structured(self, data: bytes, *, format: DocumentFormat) -> Any: ...


@dataclass
class ProcessDocumentsRequest(TenantScopedRequestDTO):
    """Request to process a batch of documents."""

    documents: List[bytes]
    format: DocumentFormat = DocumentFormat.AUTO


@dataclass
class ProcessDocumentsResponse(BaseResponseDTO):
    """Response with parsed document contents."""

    parsed_documents: List[Any] | None = None


class ProcessDocumentsUseCase(
    BaseUseCase[ProcessDocumentsRequest, ProcessDocumentsResponse]
):
    """Use case for multi-format document processing."""

    def __init__(self, parser: DocumentParserPort, tracer: TracingPort) -> None:
        super().__init__()
        self.parser = parser
        self.tracer = tracer

    def _validate_request_internal(self, request: ProcessDocumentsRequest) -> None:
        if not request.documents:
            raise ValidationError(message="No documents provided", field="documents")

    async def _execute_internal(
        self, request: ProcessDocumentsRequest
    ) -> ProcessDocumentsResponse:
        with self.tracer.start_span(
            name="process_documents",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        ) as span:
            try:
                parsed: List[Any] = []
                for data in request.documents:
                    fmt = request.format
                    if fmt == DocumentFormat.AUTO:
                        fmt = self.parser.detect_format(data)
                    if fmt == DocumentFormat.PDF:
                        parsed.append(self.parser.parse_pdf(data))
                    elif fmt == DocumentFormat.TEXT:
                        parsed.append(self.parser.parse_text(data))
                    elif fmt in (DocumentFormat.JSON, DocumentFormat.CSV):
                        parsed.append(self.parser.parse_structured(data, format=fmt))
                    else:
                        raise ValidationError(
                            message=f"Unsupported document format: {fmt}",
                            field="format",
                        )

                return ProcessDocumentsResponse(
                    success=True,
                    processing_time_ms=span.duration_ms,
                    parsed_documents=parsed,
                )
            except Exception as e:
                if isinstance(e, ValidationError):
                    raise
                raise ApplicationError(
                    message=f"Failed to process documents: {e}",
                    error_code="DOCUMENT_PROCESSING_FAILED",
                )
