from abc import ABC, abstractmethod
from typing import Any, Dict, List


class StructRAGRouterPort(ABC):
    """Port for selecting optimal structure type for a query."""

    @abstractmethod
    def select_structure(
        self, *, query: str, documents: List[str], tenant_id: str
    ) -> str:
        """Choose the best structure type given a query and documents."""
        ...


class StructRAGDecompositionPort(ABC):
    """Port for decomposing complex questions."""

    @abstractmethod
    def decompose_question(
        self, *, query: str, documents: List[str], tenant_id: str
    ) -> List[str]:
        """Break a complex query into simpler subqueries."""
        ...


class StructRAGStructurizerPort(ABC):
    """Port for constructing structured knowledge."""

    @abstractmethod
    def structurize(
        self,
        *,
        documents: List[str],
        structure_type: str,
        tenant_id: str,
        data_id: str,
    ) -> str:
        """Convert documents to a structured representation."""
        ...


class StructRAGTrainingPipelinePort(ABC):
    """Port for generating router training data."""

    @abstractmethod
    def generate_router_training_data(
        self, *, documents: List[str], tenant_id: str
    ) -> List[Dict[str, Any]]:
        """Generate training data for router preference learning."""
        ...


class StructRAGMultiHopReasoningPort(ABC):
    """Port for multi-hop reasoning over structured knowledge."""

    @abstractmethod
    def answer(
        self,
        *,
        query: str,
        documents: List[str],
        tenant_id: str,
        max_hops: int = 2,
    ) -> str:
        """Answer a query using multi-hop reasoning."""
        ...


class StructRAGStatisticalAnalysisPort(ABC):
    """Port for statistical analysis over tabular knowledge."""

    @abstractmethod
    def analyze(
        self, *, query: str, documents: List[str], tenant_id: str
    ) -> Dict[str, Any]:
        """Perform statistical analysis to answer the query."""
        ...
