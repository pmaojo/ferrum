"""Base use case class with common functionality for all use cases."""

from abc import ABC, abstractmethod
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Generic, TypeVar, cast

from domain.exceptions import ValidationError

# Generic type variables for request and response
RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")


class BaseUseCase(Generic[RequestT, ResponseT], ABC):
    """Base class for all application use cases.

    This class provides common functionality for validation, error handling,
    and execution flow that can be reused across all use cases.

    Attributes:
        logger: Logger instance for the use case
    """

    def __init__(self):
        """Initialize the base use case."""
        # Logger could be injected here if needed

    async def execute(self, request: RequestT) -> ResponseT:
        """Execute the use case with validation and error handling.

        This method implements the template pattern, defining the standard
        flow for all use cases while allowing specific steps to be
        overridden by subclasses.

        Args:
            request: The input request object

        Returns:
            The response object

        Raises:
            ValidationError: If the request is invalid
            Various domain exceptions: Based on business logic
        """
        # Validate the request
        self.validate_request(request)

        # Execute the business logic
        return await self._execute_internal(request)

    def validate_request(self, request: RequestT) -> None:
        """Validate the request object.

        This method performs common validation checks and then calls
        the use case specific validation method.

        Args:
            request: The input request object

        Raises:
            ValidationError: If the request is invalid
        """
        # Check if request is None
        if request is None:
            raise ValidationError("Request cannot be None")

        # Call use case specific validation
        self._validate_request_internal(request)

    @abstractmethod
    async def _execute_internal(self, request: RequestT) -> ResponseT:
        """Execute the use case business logic.

        This method must be implemented by all subclasses to provide
        the specific business logic for the use case.

        Args:
            request: The validated input request object

        Returns:
            The response object
        """

    def _validate_request_internal(self, request: RequestT) -> None:
        """Validate the request object with use case specific rules.

        This method should be overridden by subclasses to provide
        specific validation rules for the use case.

        Args:
            request: The input request object

        Raises:
            ValidationError: If the request is invalid
        """
        # Default implementation does nothing

    def to_dict(self, obj: Any) -> Dict[str, Any]:
        """Convert an object to a dictionary.

        This utility method helps with serializing response objects.

        Args:
            obj: The object to convert

        Returns:
            Dictionary representation of the object
        """
        if is_dataclass(obj):
            return asdict(obj)
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        else:
            return cast(Dict[str, Any], obj)
