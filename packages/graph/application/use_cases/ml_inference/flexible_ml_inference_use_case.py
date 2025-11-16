"""Use case for flexible ML model inference across different domains."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from application.exceptions import ValidationError
from application.ports import (
    AuditLoggingPort,
    AuthorizationPort,
    MLInferencePort,
    SensorAnalysisPort,
)
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO

logger = logging.getLogger(__name__)


@dataclass
class FlexibleMLInferenceRequestDTO:
    """Request DTO for flexible ML inference."""

    tenant_id: str
    user_id: str
    model_id: str
    task_type: str
    provider: str = "huggingface"
    inputs: Union[str, Dict[str, Any], List[Any], bytes] = None
    parameters: Optional[Dict[str, Any]] = None
    domain: Optional[str] = None  # e.g., "medical", "iot", "creative"


@dataclass
class MLInferenceResultDTO:
    """DTO for ML inference results."""

    model_id: str
    task_type: str
    provider: str
    result: Dict[str, Any]
    confidence_scores: Optional[List[float]] = None
    processing_time_ms: Optional[int] = None


@dataclass
class FlexibleMLInferenceResponseDTO(BaseResponseDTO):
    """Response DTO for flexible ML inference."""

    result: Optional[MLInferenceResultDTO] = None
    domain_insights: Optional[Dict[str, Any]] = None


class FlexibleMLInferenceUseCase(BaseUseCase):
    """Use case for running inference on any ML model with domain-specific enhancements."""

    def __init__(
        self,
        ml_inference_port: MLInferencePort,
        sensor_analysis_port: Optional[SensorAnalysisPort] = None,
        authorization_port: Optional[AuthorizationPort] = None,
        audit_port: Optional[AuditLoggingPort] = None,
    ):
        self.ml_inference_port = ml_inference_port
        self.sensor_analysis_port = sensor_analysis_port
        self.authorization_port = authorization_port
        self.audit_port = audit_port

    async def execute(
        self, request: FlexibleMLInferenceRequestDTO
    ) -> FlexibleMLInferenceResponseDTO:
        """Execute ML inference with domain-specific processing."""

        # Validate request
        self._validate_request(request)

        # Authorization check
        if self.authorization_port:
            await self._check_authorization(request)

        try:
            # Prepare model configuration
            from application.ports.ml_inference import MLModelConfig

            model_config = MLModelConfig(
                model_id=request.model_id,
                task_type=request.task_type,
                provider=request.provider,
                parameters=request.parameters,
            )

            # Run inference
            inference_result = await self.ml_inference_port.infer(
                model_config=model_config,
                inputs=request.inputs,
                tenant_id=request.tenant_id,
            )

            # Apply domain-specific post-processing
            domain_insights = await self._apply_domain_processing(
                request, inference_result
            )

            # Create result DTO
            result_dto = MLInferenceResultDTO(
                model_id=request.model_id,
                task_type=request.task_type,
                provider=request.provider,
                result=inference_result,
                confidence_scores=self._extract_confidence_scores(inference_result),
            )

            # Audit logging
            if self.audit_port:
                await self._log_inference(request, result_dto)

            return FlexibleMLInferenceResponseDTO(
                success=True, result=result_dto, domain_insights=domain_insights
            )

        except Exception as e:
            logger.error(f"ML inference failed: {e}")
            return FlexibleMLInferenceResponseDTO(
                success=False, error=f"Inference failed: {str(e)}"
            )

    def _validate_request(self, request: FlexibleMLInferenceRequestDTO):
        """Validate the inference request."""
        if not request.model_id:
            raise ValidationError("model_id is required")
        if not request.task_type:
            raise ValidationError("task_type is required")
        if request.inputs is None:
            raise ValidationError("inputs are required")

    async def _apply_domain_processing(
        self, request: FlexibleMLInferenceRequestDTO, inference_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Apply domain-specific post-processing."""

        if not request.domain:
            return None

        insights = {}

        if request.domain == "medical":
            insights = await self._process_medical_results(request, inference_result)
        elif request.domain == "iot":
            insights = await self._process_iot_results(request, inference_result)
        elif request.domain == "creative":
            insights = await self._process_creative_results(request, inference_result)

        return insights if insights else None

    async def _process_medical_results(
        self, request: FlexibleMLInferenceRequestDTO, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process medical/disease detection results."""

        insights = {
            "domain": "medical",
            "risk_assessment": "low",  # Default
            "recommendations": [],
        }

        if "result" in result and isinstance(result["result"], list):
            predictions = result["result"]
            max_confidence = max([p.get("score", 0) for p in predictions], default=0)

            if max_confidence > 0.8:
                insights["risk_assessment"] = "high"
                insights["recommendations"].append("Consult healthcare professional")
            elif max_confidence > 0.5:
                insights["risk_assessment"] = "medium"
                insights["recommendations"].append("Monitor condition")

        return insights

    async def _process_iot_results(
        self, request: FlexibleMLInferenceRequestDTO, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process IoT sensor analysis results."""

        insights = {"domain": "iot", "sensor_health": "normal", "alerts": []}

        if self.sensor_analysis_port and "anomaly" in request.task_type.lower():
            # Additional sensor-specific analysis
            sensor_result = await self.sensor_analysis_port.analyze_sensor_data(
                sensor_data=request.inputs,
                analysis_type="anomaly",
                tenant_id=request.tenant_id,
            )
            insights["detailed_analysis"] = sensor_result

        return insights

    async def _process_creative_results(
        self, request: FlexibleMLInferenceRequestDTO, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process creative content analysis results."""

        return {
            "domain": "creative",
            "content_type": request.task_type,
            "enhancement_suggestions": [],
            "style_analysis": result.get("result", {}),
        }

    def _extract_confidence_scores(
        self, result: Dict[str, Any]
    ) -> Optional[List[float]]:
        """Extract confidence scores from inference result."""
        if "result" in result and isinstance(result["result"], list):
            return [item.get("score", 0.0) for item in result["result"]]
        return None

    async def _check_authorization(self, request: FlexibleMLInferenceRequestDTO):
        """Check if user is authorized for ML inference."""
        # Implement authorization logic

    async def _log_inference(
        self, request: FlexibleMLInferenceRequestDTO, result: MLInferenceResultDTO
    ):
        """Log the inference for audit purposes."""
        # Implement audit logging
