"""Use case for executing raw Gremlin traversals."""

from dataclasses import dataclass
from typing import Any, Dict, List

from application.exceptions import ValidationError
from application.ports import GraphTraversalPort


@dataclass
class ExecuteGremlinQueryRequest:
    """Request object for executing a Gremlin query."""

    query: str


@dataclass
class ExecuteGremlinQueryResponse:
    """Response object containing traversal results."""

    records: List[Dict[str, Any]]


class ExecuteGremlinQueryUseCase:
    """Use case coordinating Gremlin query execution via a traversal port."""

    def __init__(self, traversal_port: GraphTraversalPort) -> None:
        self._traversal_port = traversal_port

    def execute(
        self, request: ExecuteGremlinQueryRequest
    ) -> ExecuteGremlinQueryResponse:
        """Validate and run the traversal."""
        self._validate_request(request)
        result = self._traversal_port.execute_traversal(request.query)
        return ExecuteGremlinQueryResponse(records=result)

    def _validate_request(self, request: ExecuteGremlinQueryRequest) -> None:
        if not request.query or not request.query.strip():
            raise ValidationError(message="Query cannot be empty", field="query")
