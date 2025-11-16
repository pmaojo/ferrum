from unittest.mock import Mock

import pytest

from application.use_cases.execute_gremlin_query_use_case import (
    ExecuteGremlinQueryRequest,
    ExecuteGremlinQueryUseCase,
)
from application.exceptions import ValidationError
from application.ports import GraphTraversalPort


class TestExecuteGremlinQueryUseCase:
    @pytest.fixture
    def mock_port(self) -> Mock:
        port = Mock(spec=GraphTraversalPort)
        port.execute_traversal.return_value = [{"v": 1}]
        return port

    def test_execute_success(self, mock_port: Mock) -> None:
        use_case = ExecuteGremlinQueryUseCase(mock_port)
        request = ExecuteGremlinQueryRequest(query="g.V().limit(1)")

        response = use_case.execute(request)

        mock_port.execute_traversal.assert_called_once_with("g.V().limit(1)")
        assert response.records == [{"v": 1}]

    def test_validation_error_on_empty_query(self, mock_port: Mock) -> None:
        use_case = ExecuteGremlinQueryUseCase(mock_port)
        with pytest.raises(ValidationError):
            use_case.execute(ExecuteGremlinQueryRequest(query=""))

