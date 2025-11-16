"""Use case for creating and managing adaptive training loops."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from adapters.llm.intelligent_fallback_adapter import IntelligentFallbackAdapter
from application.ports import MessageBusPort, TracingPort
from domain.adaptive_training_orchestrator import (
    AdaptiveTrainingOrchestrator,
    TrainingFeedback,
)
from domain.agent_training_loop import AgentCoordinationTrainingLoop

logger = logging.getLogger(__name__)


class CreateAdaptiveTrainingLoopUseCase:
    """Use case for creating and managing adaptive training loops."""

    def __init__(
        self,
        llm_adapter: IntelligentFallbackAdapter,
        message_bus: MessageBusPort,
        tracer: Optional[TracingPort] = None,
    ):
        self.training_orchestrator = AdaptiveTrainingOrchestrator(
            llm_adapter=llm_adapter, message_bus=message_bus, tracer=tracer
        )
        self.agent_training = AgentCoordinationTrainingLoop(
            agent_coordinator=None,  # Would be injected in real implementation
            message_bus=message_bus,
            tracer=tracer,
        )

    async def create_ontology_training_loop(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        feedback_threshold: int = 50,
        retraining_interval_hours: int = 24,
    ) -> str:
        """Create an ontology evolution training loop."""

        try:
            loop_id = await self.training_orchestrator.start_ontology_evolution_loop(
                kg_id=kg_id,
                tenant_id=tenant_id,
                feedback_threshold=feedback_threshold,
                retraining_interval_hours=retraining_interval_hours,
            )

            logger.info(f"Created ontology training loop {loop_id} for KG {kg_id}")
            return loop_id

        except Exception as e:
            logger.error(f"Failed to create ontology training loop: {e}")
            raise

    async def create_query_optimization_loop(
        self,
        *,
        tenant_id: str,
        performance_threshold: float = 0.8,
        sample_size: int = 100,
    ) -> str:
        """Create a query optimization training loop."""

        try:
            loop_id = await self.training_orchestrator.start_query_optimization_loop(
                tenant_id=tenant_id,
                performance_threshold=performance_threshold,
                sample_size=sample_size,
            )

            logger.info(f"Created query optimization loop {loop_id}")
            return loop_id

        except Exception as e:
            logger.error(f"Failed to create query optimization loop: {e}")
            raise

    async def create_embedding_refinement_loop(
        self,
        *,
        tenant_id: str,
        similarity_threshold: float = 0.85,
        batch_size: int = 1000,
    ) -> str:
        """Create an embedding refinement training loop."""

        try:
            loop_id = await self.training_orchestrator.start_embedding_refinement_loop(
                tenant_id=tenant_id,
                similarity_threshold=similarity_threshold,
                batch_size=batch_size,
            )

            logger.info(f"Created embedding refinement loop {loop_id}")
            return loop_id

        except Exception as e:
            logger.error(f"Failed to create embedding refinement loop: {e}")
            raise

    async def submit_training_feedback(
        self,
        *,
        session_id: str,
        feedback_type: str,
        input_data: Dict[str, Any],
        expected_output: Dict[str, Any],
        actual_output: Dict[str, Any],
        quality_score: float,
        tenant_id: str,
    ) -> None:
        """Submit feedback for training loop improvement."""

        try:
            feedback = TrainingFeedback(
                session_id=session_id,
                feedback_type=feedback_type,
                input_data=input_data,
                expected_output=expected_output,
                actual_output=actual_output,
                quality_score=quality_score,
                tenant_id=tenant_id,
                timestamp=datetime.now(),
            )

            await self.training_orchestrator.collect_feedback(feedback)

            logger.info(f"Submitted training feedback for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to submit training feedback: {e}")
            raise

    def get_training_loops_status(self, tenant_id: str) -> Dict[str, Any]:
        """Get status of all training loops for a tenant."""

        try:
            active_loops = self.training_orchestrator.list_active_loops(tenant_id)
            agent_training_status = self.agent_training.get_training_status()

            return {
                "active_loops": active_loops,
                "agent_coordination": agent_training_status,
                "total_active": len(active_loops),
            }

        except Exception as e:
            logger.error(f"Failed to get training loops status: {e}")
            raise

    async def stop_training_loop(self, loop_id: str) -> None:
        """Stop a specific training loop."""

        try:
            await self.training_orchestrator.stop_training_loop(loop_id)
            logger.info(f"Stopped training loop {loop_id}")

        except Exception as e:
            logger.error(f"Failed to stop training loop {loop_id}: {e}")
            raise
