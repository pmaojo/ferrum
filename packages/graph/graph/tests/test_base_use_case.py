"""Unit tests for the base use case class."""

import pytest
import anyio
from dataclasses import dataclass
from typing import Optional

from application.use_cases.base_use_case import BaseUseCase
from domain.exceptions import ValidationError


@dataclass
class TestRequest:
    """Test request class for unit tests."""
    name: str
    value: int
    optional_field: Optional[str] = None


@dataclass
class TestResponse:
    """Test response class for unit tests."""
    result: str
    success: bool


class TestBaseUseCase(BaseUseCase[TestRequest, TestResponse]):
    """Test implementation of BaseUseCase for unit tests."""

    def _validate_request_internal(self, request: TestRequest) -> None:
        """Validate the test request."""
        if not request.name:
            raise ValidationError("Name cannot be empty")

        if request.value <= 0:
            raise ValidationError("Value must be positive", param="value")

    async def _execute_internal(self, request: TestRequest) -> TestResponse:
        """Execute the test use case."""
        result = f"Processed {request.name} with value {request.value}"
        if request.optional_field:
            result += f" and {request.optional_field}"

        return TestResponse(result=result, success=True)


class FailingUseCase(BaseUseCase[TestRequest, TestResponse]):
    """Test implementation that fails during execution."""

    def _validate_request_internal(self, request: TestRequest) -> None:
        """Validation passes."""
        pass

    async def _execute_internal(self, request: TestRequest) -> TestResponse:
        """Execution fails."""
        raise ValueError("Execution failed")


@pytest.mark.anyio(backends=["asyncio"])
async def test_successful_execution():
    """Test successful execution of a use case."""
    # Arrange
    use_case = TestBaseUseCase()
    request = TestRequest(name="test", value=42, optional_field="optional")

    # Act
    response = await use_case.execute(request)

    # Assert
    assert response.success is True
    assert response.result == "Processed test with value 42 and optional"


@pytest.mark.anyio(backends=["asyncio"])
async def test_validation_error_empty_name():
    """Test validation error when name is empty."""
    # Arrange
    use_case = TestBaseUseCase()
    request = TestRequest(name="", value=42)

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        await use_case.execute(request)

    assert "Name cannot be empty" in str(exc_info.value)


@pytest.mark.anyio(backends=["asyncio"])
async def test_validation_error_negative_value():
    """Test validation error when value is negative."""
    # Arrange
    use_case = TestBaseUseCase()
    request = TestRequest(name="test", value=-1)

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        await use_case.execute(request)

    assert "Value must be positive" in str(exc_info.value)
    assert exc_info.value.param == "value"


@pytest.mark.anyio(backends=["asyncio"])
async def test_none_request():
    """Test validation error when request is None."""
    # Arrange
    use_case = TestBaseUseCase()

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        await use_case.execute(None)

    assert "Request cannot be None" in str(exc_info.value)


@pytest.mark.anyio(backends=["asyncio"])
async def test_execution_error():
    """Test error during execution."""
    # Arrange
    use_case = FailingUseCase()
    request = TestRequest(name="test", value=42)

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        await use_case.execute(request)

    assert "Execution failed" in str(exc_info.value)


def test_to_dict_with_dataclass():
    """Test to_dict method with a dataclass."""
    # Arrange
    use_case = TestBaseUseCase()
    obj = TestRequest(name="test", value=42)

    # Act
    result = use_case.to_dict(obj)

    # Assert
    assert result == {"name": "test", "value": 42, "optional_field": None}


def test_to_dict_with_regular_class():
    """Test to_dict method with a regular class."""
    # Arrange
    class RegularClass:
        def __init__(self):
            self.name = "test"
            self.value = 42

    use_case = TestBaseUseCase()
    obj = RegularClass()

    # Act
    result = use_case.to_dict(obj)

    # Assert
    assert result == {"name": "test", "value": 42}


def test_to_dict_with_dict():
    """Test to_dict method with a dictionary."""
    # Arrange
    use_case = TestBaseUseCase()
    obj = {"name": "test", "value": 42}

    # Act
    result = use_case.to_dict(obj)

    # Assert
    assert result == {"name": "test", "value": 42}