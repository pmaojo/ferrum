
"""Agent coordination training loop for multi-agent GraphRAG system."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from domain.agent_coordinator import AgentCoordinator, CoordinationException
from application.ports import MessageBusPort, TracingPort

logger = logging.getLogger(__name__)


@dataclass
class CoordinationFeedback:
    """Feedback data for agent coordination."""
    session_id: str
    agent_types: List[str]
    coordination_pattern: str
    success_rate: float
    latency_ms: float
    quality_score: float
    tenant_id: str
    timestamp: datetime


class AgentCoordinationTrainingLoop:
    """Training loop for improving agent coordination patterns."""

    def __init__(
        self,
        agent_coordinator: AgentCoordinator,
        message_bus: MessageBusPort,
        tracer: Optional[TracingPort] = None
    ):
        self.agent_coordinator = agent_coordinator
        self.message_bus = message_bus
        self.tracer = tracer
        self.coordination_patterns = {}
        self.feedback_history = []
        self.training_active = False

    async def start_coordination_training(
        self,
        *,
        tenant_id: str,
        target_success_rate: float = 0.9,
        min_sessions_for_retraining: int = 20
    ) -> None:
        """Start agent coordination training loop."""
        
        self.training_active = True
        self.target_success_rate = target_success_rate
        self.min_sessions = min_sessions_for_retraining
        self.tenant_id = tenant_id
        
        logger.info(f"Started agent coordination training for tenant {tenant_id}")
        
        # Start monitoring coordination patterns
        await self._monitor_coordination_patterns()

    async def collect_coordination_feedback(
        self,
        feedback: CoordinationFeedback
    ) -> None:
        """Collect feedback about agent coordination performance."""
        
        self.feedback_history.append(feedback)
        
        # Update pattern statistics
        pattern_key = f"{feedback.coordination_pattern}_{len(feedback.agent_types)}"
        if pattern_key not in self.coordination_patterns:
            self.coordination_patterns[pattern_key] = {
                "successes": 0,
                "failures": 0,
                "avg_latency": 0,
                "avg_quality": 0,
                "total_sessions": 0
            }
        
        pattern_stats = self.coordination_patterns[pattern_key]
        pattern_stats["total_sessions"] += 1
        
        if feedback.success_rate >= self.target_success_rate:
            pattern_stats["successes"] += 1
        else:
            pattern_stats["failures"] += 1
        
        # Update running averages
        pattern_stats["avg_latency"] = (
            (pattern_stats["avg_latency"] * (pattern_stats["total_sessions"] - 1) + feedback.latency_ms) /
            pattern_stats["total_sessions"]
        )
        
        pattern_stats["avg_quality"] = (
            (pattern_stats["avg_quality"] * (pattern_stats["total_sessions"] - 1) + feedback.quality_score) /
            pattern_stats["total_sessions"]
        )
        
        # Check if retraining is needed
        if pattern_stats["total_sessions"] >= self.min_sessions:
            success_rate = pattern_stats["successes"] / pattern_stats["total_sessions"]
            if success_rate < self.target_success_rate:
                await self._trigger_coordination_retraining(pattern_key)

    async def _trigger_coordination_retraining(self, pattern_key: str) -> None:
        """Trigger retraining for underperforming coordination patterns."""
        
        pattern_stats = self.coordination_patterns[pattern_key]
        
        # Analyze failures and suggest improvements
        recent_failures = [
            f for f in self.feedback_history[-50:]  # Last 50 sessions
            if f"{f.coordination_pattern}_{len(f.agent_types)}" == pattern_key
            and f.success_rate < self.target_success_rate
        ]
        
        if not recent_failures:
            return
        
        # Generate training recommendations
        training_recommendations = await self._generate_coordination_improvements(
            pattern_key, recent_failures, pattern_stats
        )
        
        # Apply improvements
        await self._apply_coordination_improvements(pattern_key, training_recommendations)
        
        # Reset pattern statistics to start fresh evaluation
        pattern_stats["successes"] = 0
        pattern_stats["failures"] = 0
        pattern_stats["total_sessions"] = 0
        
        logger.info(f"Retrained coordination pattern: {pattern_key}")

    async def _generate_coordination_improvements(
        self,
        pattern_key: str,
        failures: List[CoordinationFeedback],
        stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate improvements for coordination patterns."""
        
        # Analyze failure patterns
        common_issues = {}
        for failure in failures:
            # Extract common failure characteristics
            if failure.latency_ms > stats["avg_latency"] * 2:
                common_issues["high_latency"] = common_issues.get("high_latency", 0) + 1
            if failure.quality_score < 0.7:
                common_issues["low_quality"] = common_issues.get("low_quality", 0) + 1
        
        recommendations = {
            "pattern_key": pattern_key,
            "identified_issues": common_issues,
            "suggested_improvements": []
        }
        
        # Generate specific recommendations
        if common_issues.get("high_latency", 0) > len(failures) * 0.5:
            recommendations["suggested_improvements"].append({
                "type": "reduce_communication_overhead",
                "description": "Optimize message passing between agents",
                "priority": "high"
            })
        
        if common_issues.get("low_quality", 0) > len(failures) * 0.3:
            recommendations["suggested_improvements"].append({
                "type": "improve_consensus_mechanism",
                "description": "Enhance agent agreement protocols",
                "priority": "medium"
            })
        
        return recommendations

    async def _apply_coordination_improvements(
        self,
        pattern_key: str,
        recommendations: Dict[str, Any]
    ) -> None:
        """Apply coordination improvements to the agent coordinator."""
        
        for improvement in recommendations["suggested_improvements"]:
            if improvement["type"] == "reduce_communication_overhead":
                # Implement communication optimization
                await self._optimize_agent_communication(pattern_key)
            elif improvement["type"] == "improve_consensus_mechanism":
                # Enhance consensus protocols
                await self._enhance_consensus_protocols(pattern_key)
        
        logger.info(f"Applied improvements for {pattern_key}")

    async def _optimize_agent_communication(self, pattern_key: str) -> None:
        """Optimize communication patterns between agents."""
        
        # Publish optimization message
        self.message_bus.publish(
            topic="agents.optimize_communication",
            message={
                "pattern_key": pattern_key,
                "optimization_type": "reduce_overhead",
                "timestamp": datetime.now().isoformat()
            },
            tenant_id=self.tenant_id
        )

    async def _enhance_consensus_protocols(self, pattern_key: str) -> None:
        """Enhance consensus mechanisms between agents."""
        
        # Publish consensus enhancement message
        self.message_bus.publish(
            topic="agents.enhance_consensus",
            message={
                "pattern_key": pattern_key,
                "enhancement_type": "improve_agreement",
                "timestamp": datetime.now().isoformat()
            },
            tenant_id=self.tenant_id
        )

    async def _monitor_coordination_patterns(self) -> None:
        """Monitor ongoing coordination patterns."""
        
        while self.training_active:
            # Analyze current patterns
            for pattern_key, stats in self.coordination_patterns.items():
                if stats["total_sessions"] > 0:
                    success_rate = stats["successes"] / stats["total_sessions"]
                    
                    if self.tracer:
                        self.tracer.record_metric(
                            name="agent_coordination_success_rate",
                            value=success_rate,
                            tenant_id=self.tenant_id,
                            pattern=pattern_key
                        )
            
            # Wait before next monitoring cycle
            await asyncio.sleep(300)  # 5 minutes

    def get_training_status(self) -> Dict[str, Any]:
        """Get current training status and statistics."""
        
        return {
            "training_active": self.training_active,
            "coordination_patterns": self.coordination_patterns,
            "total_feedback_sessions": len(self.feedback_history),
            "target_success_rate": self.target_success_rate,
            "tenant_id": self.tenant_id
        }

    def stop_training(self) -> None:
        """Stop the training loop."""
        self.training_active = False
        logger.info("Stopped agent coordination training")
