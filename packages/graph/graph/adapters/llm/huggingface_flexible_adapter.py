"""Flexible Hugging Face adapter supporting any ML model via API."""

import asyncio
import base64
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Union

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class HuggingFaceModelConfig:
    """Configuration for any Hugging Face model."""

    model_id: str
    task_type: Literal[
        "text-classification",
        "image-classification",
        "object-detection",
        "image-segmentation",
        "text-generation",
        "summarization",
        "question-answering",
        "fill-mask",
        "feature-extraction",
        "image-to-text",
        "automatic-speech-recognition",
        "audio-classification",
        "text-to-speech",
        "conversational",
        "translation",
        "zero-shot-classification",
        "sentence-similarity",
        "tabular-classification",
        "tabular-regression",
    ]
    api_url: Optional[str] = None
    use_cache: bool = True
    parameters: Optional[Dict[str, Any]] = None


class HuggingFaceFlexibleAdapter:
    """Mega-flexible adapter for any Hugging Face model via Inference API."""

    def __init__(
        self, api_token: str, base_url: str = "https://api-inference.huggingface.co"
    ):
        self.api_token = api_token
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=aiohttp.ClientTimeout(total=300),
            )
        return self.session

    async def infer(
        self,
        model_config: HuggingFaceModelConfig,
        inputs: Union[str, bytes, Dict[str, Any], List[Any]],
        tenant_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Universal inference method for any HF model."""

        session = await self._get_session()
        model_url = (
            model_config.api_url or f"{self.base_url}/models/{model_config.model_id}"
        )

        # Prepare payload based on input type
        payload = self._prepare_payload(model_config, inputs, **kwargs)

        try:
            async with session.post(model_url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "model_id": model_config.model_id,
                        "task_type": model_config.task_type,
                        "tenant_id": tenant_id,
                        "result": result,
                        "status": "success",
                    }
                elif response.status == 503:
                    # Model loading, retry after delay
                    await asyncio.sleep(2)
                    return await self.infer(model_config, inputs, tenant_id, **kwargs)
                else:
                    error_text = await response.text()
                    logger.error(f"HF API error {response.status}: {error_text}")
                    return {
                        "model_id": model_config.model_id,
                        "status": "error",
                        "error": error_text,
                    }

        except Exception as e:
            logger.error(f"Error calling HF model {model_config.model_id}: {e}")
            return {
                "model_id": model_config.model_id,
                "status": "error",
                "error": str(e),
            }

    def _prepare_payload(
        self,
        model_config: HuggingFaceModelConfig,
        inputs: Union[str, bytes, Dict[str, Any], List[Any]],
        **kwargs,
    ) -> Dict[str, Any]:
        """Prepare API payload based on task type and input."""

        payload = {"inputs": inputs}

        # Add model-specific parameters
        if model_config.parameters:
            payload["parameters"] = model_config.parameters

        # Handle binary data (images, audio)
        if isinstance(inputs, bytes):
            payload["inputs"] = base64.b64encode(inputs).decode()

        # Add caching preference
        if not model_config.use_cache:
            payload["options"] = {"use_cache": False}

        # Add any additional parameters
        if kwargs:
            if "parameters" not in payload:
                payload["parameters"] = {}
            payload["parameters"].update(kwargs)

        return payload

    async def close(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()


# Specialized adapters for common use cases
class HuggingFaceDiseaseDetectionAdapter(HuggingFaceFlexibleAdapter):
    """Specialized adapter for skin disease detection."""

    def __init__(self, api_token: str, model_id: str = "google/vit-base-patch16-224"):
        super().__init__(api_token)
        self.disease_model = HuggingFaceModelConfig(
            model_id=model_id, task_type="image-classification", parameters={"top_k": 5}
        )

    async def detect_skin_disease(
        self, image_data: bytes, tenant_id: str, confidence_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """Detect skin diseases from image data."""

        result = await self.infer(self.disease_model, image_data, tenant_id)

        if result["status"] == "success":
            # Filter results by confidence
            predictions = result["result"]
            if isinstance(predictions, list):
                filtered = [
                    pred
                    for pred in predictions
                    if pred.get("score", 0) >= confidence_threshold
                ]
                result["filtered_predictions"] = filtered

        return result


class HuggingFaceSensorAnalysisAdapter(HuggingFaceFlexibleAdapter):
    """Adapter for analyzing sensor data (IoT, time series, tabular data)."""

    def __init__(self, api_token: str):
        super().__init__(api_token)

    async def analyze_sensor_data(
        self,
        sensor_data: Dict[str, Any],
        analysis_type: Literal["anomaly", "classification", "regression"],
        tenant_id: str,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze sensor data using appropriate ML models."""

        # Choose model based on analysis type
        if not model_id:
            model_id = {
                "anomaly": "microsoft/DialoGPT-medium",  # Can be customized
                "classification": "microsoft/table-transformer-structure-recognition",
                "regression": "microsoft/table-transformer-structure-recognition",
            }.get(analysis_type, "microsoft/DialoGPT-medium")

        task_type = {
            "anomaly": "text-classification",
            "classification": "tabular-classification",
            "regression": "tabular-regression",
        }.get(analysis_type, "text-classification")

        model_config = HuggingFaceModelConfig(
            model_id=model_id,
            task_type=task_type,
            parameters={"return_all_scores": True},
        )

        return await self.infer(model_config, sensor_data, tenant_id)
