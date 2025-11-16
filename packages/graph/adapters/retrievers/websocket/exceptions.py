from typing import Any, Dict


class StreamingException(Exception):
    """Base exception for streaming operations."""

    def __init__(self, message: str, error_code: str, context: Dict[str, Any]):
        self.message = message
        self.error_code = error_code
        self.context = context
        super().__init__(message)


class BufferOverflowError(StreamingException):
    """Exception raised when event buffer is full."""

    def __init__(self, buffer_size: int, context: Dict[str, Any]):
        super().__init__(
            message=f"Event buffer overflow (size: {buffer_size})",
            error_code="BUFFER_OVERFLOW",
            context=context,
        )
