"""Health check ports for system health monitoring."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Protocol


class HealthStatus(str, Enum):
    """Health status enum for system components."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


@dataclass
class ComponentHealth:
    """Health information for a system component."""

    name: str
    status: HealthStatus
    details: Dict[str, Any]
    message: str = ""


class HealthCheckPort(Protocol):
    """Port for health check operations."""

    def check_database_health(self) -> ComponentHealth:
        """Check the health of the database."""
        ...

    def check_cache_health(self) -> ComponentHealth:
        """Check the health of the cache."""
        ...

    def check_graph_db_health(self) -> ComponentHealth:
        """Check the health of the graph database."""
        ...

    def check_llm_health(self) -> ComponentHealth:
        """Check the health of the LLM services."""
        ...

    def check_component_health(self, component_name: str) -> ComponentHealth:
        """Check the health of a specific component."""
        ...

    def get_overall_health(self) -> HealthStatus:
        """Get the overall health status of the system."""
        ...
