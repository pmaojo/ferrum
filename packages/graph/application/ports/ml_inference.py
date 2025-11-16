"""Port interfaces for flexible ML model inference."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Union


@dataclass
class MLModelConfig:
    """Configuration for any ML model."""

    model_id: str
    task_type: str
    provider: Literal["huggingface", "openai", "anthropic", "custom"]
    parameters: Optional[Dict[str, Any]] = None


class MLInferencePort(ABC):
    """Port for flexible ML model inference."""

    @abstractmethod
    async def infer(
        self,
        model_config: MLModelConfig,
        inputs: Union[str, bytes, Dict[str, Any], List[Any]],
        tenant_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Run inference on any ML model."""

    @abstractmethod
    async def batch_infer(
        self,
        model_config: MLModelConfig,
        inputs_batch: List[Union[str, bytes, Dict[str, Any]]],
        tenant_id: str,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Run batch inference."""


class SensorAnalysisPort(ABC):
    """Port for sensor data analysis."""

    @abstractmethod
    async def analyze_sensor_data(
        self,
        sensor_data: Dict[str, Any],
        analysis_type: Literal[
            "anomaly", "classification", "regression", "forecasting"
        ],
        tenant_id: str,
        model_config: Optional[MLModelConfig] = None,
    ) -> Dict[str, Any]:
        """Analyze sensor data using ML models."""

    @abstractmethod
    async def detect_anomalies(
        self,
        time_series_data: List[Dict[str, Any]],
        tenant_id: str,
        sensitivity: float = 0.5,
    ) -> Dict[str, Any]:
        """Detect anomalies in sensor data."""


class CustomMLModelPort(ABC):
    """Port for integrating custom ML models."""

    @abstractmethod
    async def register_model(
        self,
        model_id: str,
        model_endpoint: str,
        model_config: Dict[str, Any],
        tenant_id: str,
    ) -> bool:
        """Register a custom ML model."""

    @abstractmethod
    async def invoke_custom_model(
        self, model_id: str, inputs: Any, tenant_id: str
    ) -> Dict[str, Any]:
        """Invoke a registered custom model."""
