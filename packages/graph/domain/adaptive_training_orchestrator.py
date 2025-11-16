
"""Adaptive training orchestrator for continuous model improvement."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from application.ports import MessageBusPort, TracingPort
from domain.entities import JobStatus
from adapters.llm.intelligent_fallback_adapter import IntelligentFallbackAdapter

logger = logging.getLogger(__name__)


class TrainingLoopType(Enum):
    """Types of training loops available."""
    ONTOLOGY_EVOLUTION = "ontology_evolution"
    QUERY_OPTIMIZATION = "query_optimization"
    EMBEDDING_REFINEMENT = "embedding_refinement"
    AGENT_COORDINATION = "agent_coordination"


@dataclass
class TrainingFeedback:
    """Training feedback data structure."""
    session_id: str
    feedback_type: str
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    actual_output: Dict[str, Any]
    quality_score: float
    tenant_id: str
    timestamp: datetime


class AdaptiveTrainingOrchestrator:
    """Orchestrates continuous learning loops for model improvement."""

    def __init__(
        self,
        llm_adapter: IntelligentFallbackAdapter,
        message_bus: MessageBusPort,
        tracer: Optional[TracingPort] = None
    ):
        self.llm_adapter = llm_adapter
        self.message_bus = message_bus
        self.tracer = tracer
        self.active_loops: Dict[str, Dict[str, Any]] = {}
        self.training_data: Dict[str, List[TrainingFeedback]] = {}

    async def start_ontology_evolution_loop(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        feedback_threshold: int = 50,
        retraining_interval_hours: int = 24
    ) -> str:
        """Start continuous ontology evolution training loop."""
        
        loop_id = f"ontology_{kg_id}_{datetime.now().timestamp()}"
        
        loop_config = {
            "loop_id": loop_id,
            "type": TrainingLoopType.ONTOLOGY_EVOLUTION,
            "kg_id": kg_id,
            "tenant_id": tenant_id,
            "feedback_threshold": feedback_threshold,
            "retraining_interval": timedelta(hours=retraining_interval_hours),
            "status": JobStatus.RUNNING,
            "started_at": datetime.now(),
            "last_training": None,
            "feedback_count": 0,
            "model_version": 1
        }
        
        self.active_loops[loop_id] = loop_config
        
        # Start the feedback collection
        await self._schedule_training_check(loop_id)
        
        logger.info(f"Started ontology evolution loop {loop_id} for KG {kg_id}")
        return loop_id

    async def start_query_optimization_loop(
        self,
        *,
        tenant_id: str,
        performance_threshold: float = 0.8,
        sample_size: int = 100
    ) -> str:
        """Start continuous query optimization training loop."""
        
        loop_id = f"query_opt_{tenant_id}_{datetime.now().timestamp()}"
        
        loop_config = {
            "loop_id": loop_id,
            "type": TrainingLoopType.QUERY_OPTIMIZATION,
            "tenant_id": tenant_id,
            "performance_threshold": performance_threshold,
            "sample_size": sample_size,
            "status": JobStatus.RUNNING,
            "started_at": datetime.now(),
            "query_patterns": {},
            "optimization_history": []
        }
        
        self.active_loops[loop_id] = loop_config
        
        # Start collecting query performance data
        await self._start_query_monitoring(loop_id)
        
        logger.info(f"Started query optimization loop {loop_id} for tenant {tenant_id}")
        return loop_id

    async def start_embedding_refinement_loop(
        self,
        *,
        tenant_id: str,
        similarity_threshold: float = 0.85,
        batch_size: int = 1000
    ) -> str:
        """Start continuous embedding refinement training loop."""
        
        loop_id = f"embedding_{tenant_id}_{datetime.now().timestamp()}"
        
        loop_config = {
            "loop_id": loop_id,
            "type": TrainingLoopType.EMBEDDING_REFINEMENT,
            "tenant_id": tenant_id,
            "similarity_threshold": similarity_threshold,
            "batch_size": batch_size,
            "status": JobStatus.RUNNING,
            "started_at": datetime.now(),
            "embedding_quality_scores": [],
            "refinement_iterations": 0
        }
        
        self.active_loops[loop_id] = loop_config
        
        # Start embedding quality monitoring
        await self._monitor_embedding_quality(loop_id)
        
        logger.info(f"Started embedding refinement loop {loop_id} for tenant {tenant_id}")
        return loop_id

    async def collect_feedback(
        self,
        feedback: TrainingFeedback
    ) -> None:
        """Collect training feedback for continuous improvement."""
        
        loop_key = f"{feedback.feedback_type}_{feedback.tenant_id}"
        
        if loop_key not in self.training_data:
            self.training_data[loop_key] = []
        
        self.training_data[loop_key].append(feedback)
        
        # Check if we should trigger retraining
        for loop_id, config in self.active_loops.items():
            if config["tenant_id"] == feedback.tenant_id:
                config["feedback_count"] += 1
                
                if config["feedback_count"] >= config.get("feedback_threshold", 50):
                    await self._trigger_retraining(loop_id)

    async def _trigger_retraining(self, loop_id: str) -> None:
        """Trigger model retraining based on collected feedback."""
        
        config = self.active_loops[loop_id]
        loop_type = config["type"]
        
        if loop_type == TrainingLoopType.ONTOLOGY_EVOLUTION:
            await self._retrain_ontology_model(loop_id)
        elif loop_type == TrainingLoopType.QUERY_OPTIMIZATION:
            await self._retrain_query_optimizer(loop_id)
        elif loop_type == TrainingLoopType.EMBEDDING_REFINEMENT:
            await self._retrain_embedding_model(loop_id)
        
        # Reset feedback counter
        config["feedback_count"] = 0
        config["last_training"] = datetime.now()
        config["model_version"] += 1

    async def _retrain_ontology_model(self, loop_id: str) -> None:
        """Retrain ontology extraction model."""
        
        config = self.active_loops[loop_id]
        tenant_id = config["tenant_id"]
        
        # Collect training data
        training_examples = self._prepare_ontology_training_data(tenant_id)
        
        # Generate retraining prompt for the LLM
        retrain_prompt = f"""
        Based on the following feedback examples, improve entity and relationship extraction:
        
        Training Examples:
        {self._format_training_examples(training_examples)}
        
        Please analyze these examples and suggest improvements to:
        1. Entity recognition patterns
        2. Relationship extraction rules
        3. Ontology schema refinements
        
        Focus on patterns where actual output differed from expected output.
        """
        
        # Use the intelligent fallback adapter for retraining
        result = self.llm_adapter.generate(
            prompt=retrain_prompt,
            tenant_id=tenant_id,
            opts={"max_tokens": 2000, "temperature": 0.1}
        )
        
        # Apply the improvements
        await self._apply_ontology_improvements(loop_id, result)
        
        logger.info(f"Retrained ontology model for loop {loop_id}")

    async def _retrain_query_optimizer(self, loop_id: str) -> None:
        """Retrain query optimization model."""
        
        config = self.active_loops[loop_id]
        
        # Analyze query patterns and performance
        optimization_prompt = f"""
        Analyze the following query performance data and suggest optimizations:
        
        Query Patterns: {config['query_patterns']}
        Performance History: {config['optimization_history']}
        
        Suggest specific improvements for:
        1. Query rewriting strategies
        2. Index utilization
        3. Graph traversal optimization
        """
        
        result = self.llm_adapter.generate(
            prompt=optimization_prompt,
            tenant_id=config["tenant_id"],
            opts={"max_tokens": 1500}
        )
        
        await self._apply_query_optimizations(loop_id, result)
        
        logger.info(f"Retrained query optimizer for loop {loop_id}")

    async def _retrain_embedding_model(self, loop_id: str) -> None:
        """Retrain embedding model for better semantic similarity."""
        
        config = self.active_loops[loop_id]
        
        # Fine-tune embeddings based on similarity feedback
        embedding_prompt = f"""
        Based on embedding quality feedback, suggest improvements:
        
        Quality Scores: {config['embedding_quality_scores'][-100:]}  # Last 100 scores
        Current Threshold: {config['similarity_threshold']}
        
        Recommend adjustments to:
        1. Embedding dimension optimization
        2. Training data curation
        3. Similarity calculation methods
        """
        
        result = self.llm_adapter.generate(
            prompt=embedding_prompt,
            tenant_id=config["tenant_id"],
            opts={"max_tokens": 1200}
        )
        
        await self._apply_embedding_improvements(loop_id, result)
        
        logger.info(f"Retrained embedding model for loop {loop_id}")

    def _prepare_ontology_training_data(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Prepare training data for ontology model retraining."""
        
        loop_key = f"ontology_evolution_{tenant_id}"
        feedback_data = self.training_data.get(loop_key, [])
        
        training_examples = []
        for feedback in feedback_data[-100:]:  # Use last 100 examples
            training_examples.append({
                "input": feedback.input_data,
                "expected": feedback.expected_output,
                "actual": feedback.actual_output,
                "quality": feedback.quality_score
            })
        
        return training_examples

    def _format_training_examples(self, examples: List[Dict[str, Any]]) -> str:
        """Format training examples for LLM consumption."""
        
        formatted = []
        for i, example in enumerate(examples[:10]):  # Limit to 10 examples
            formatted.append(f"""
            Example {i+1}:
            Input: {example['input']}
            Expected: {example['expected']}
            Actual: {example['actual']}
            Quality Score: {example['quality']}
            """)
        
        return "\n".join(formatted)

    async def _schedule_training_check(self, loop_id: str) -> None:
        """Schedule periodic training checks."""
        
        # Publish message to check training conditions
        self.message_bus.publish(
            topic="training.schedule_check",
            message={
                "loop_id": loop_id,
                "check_time": (datetime.now() + timedelta(hours=1)).isoformat()
            },
            tenant_id=self.active_loops[loop_id]["tenant_id"]
        )

    async def _start_query_monitoring(self, loop_id: str) -> None:
        """Start monitoring query performance."""
        
        config = self.active_loops[loop_id]
        
        # Set up query performance tracking
        self.message_bus.publish(
            topic="training.start_query_monitoring",
            message={
                "loop_id": loop_id,
                "tenant_id": config["tenant_id"],
                "performance_threshold": config["performance_threshold"]
            },
            tenant_id=config["tenant_id"]
        )

    async def _monitor_embedding_quality(self, loop_id: str) -> None:
        """Monitor embedding quality metrics."""
        
        config = self.active_loops[loop_id]
        
        # Set up embedding quality monitoring
        self.message_bus.publish(
            topic="training.monitor_embeddings",
            message={
                "loop_id": loop_id,
                "tenant_id": config["tenant_id"],
                "similarity_threshold": config["similarity_threshold"]
            },
            tenant_id=config["tenant_id"]
        )

    async def _apply_ontology_improvements(self, loop_id: str, improvements: str) -> None:
        """Apply ontology model improvements."""
        logger.info(f"Applying ontology improvements for {loop_id}: {improvements[:200]}...")

    async def _apply_query_optimizations(self, loop_id: str, optimizations: str) -> None:
        """Apply query optimization improvements."""
        logger.info(f"Applying query optimizations for {loop_id}: {optimizations[:200]}...")

    async def _apply_embedding_improvements(self, loop_id: str, improvements: str) -> None:
        """Apply embedding model improvements."""
        logger.info(f"Applying embedding improvements for {loop_id}: {improvements[:200]}...")

    def get_loop_status(self, loop_id: str) -> Dict[str, Any]:
        """Get status of a training loop."""
        return self.active_loops.get(loop_id, {})

    def list_active_loops(self, tenant_id: str) -> List[Dict[str, Any]]:
        """List all active training loops for a tenant."""
        return [
            config for config in self.active_loops.values()
            if config.get("tenant_id") == tenant_id
        ]

    async def stop_training_loop(self, loop_id: str) -> None:
        """Stop a training loop."""
        if loop_id in self.active_loops:
            self.active_loops[loop_id]["status"] = JobStatus.CANCELLED
            logger.info(f"Stopped training loop {loop_id}")
