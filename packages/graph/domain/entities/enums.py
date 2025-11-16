from enum import Enum, auto


class ScientificDomain(Enum):
    """Scientific domains for knowledge graph specialization."""

    BIOLOGY = "biology"
    CHEMISTRY = "chemistry"
    PHYSICS = "physics"
    MEDICINE = "medicine"
    ENVIRONMENTAL_SCIENCE = "environmental_science"
    ASTRONOMY = "astronomy"
    GENERAL = "general"


class GraphStreamEventType(Enum):
    """Types of graph stream events for real-time updates."""

    NODE_ADDED = auto()
    EDGE_ADDED = auto()
    PATH_HIGHLIGHTED = auto()
    COMMUNITY_UPDATED = auto()
    RENDER_COMPLETED = auto()


class DataRetentionTarget(Enum):
    """Categories of data affected by retention policies."""

    LOGS = "logs"
    BACKUPS = "backups"

