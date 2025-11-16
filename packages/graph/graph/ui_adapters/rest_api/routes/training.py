
"""REST API routes for adaptive training loops."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ui_adapters.rest_api.dependencies import (
    get_llm_adapter,
    get_message_bus,
    get_tracer
)
from application.use_cases.training.create_adaptive_training_loop_use_case import (
    CreateAdaptiveTrainingLoopUseCase
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/training", tags=["training"])


class CreateOntologyTrainingRequest(BaseModel):
    kg_id: str
    tenant_id: str
    feedback_threshold: int = 50
    retraining_interval_hours: int = 24


class CreateQueryOptimizationRequest(BaseModel):
    tenant_id: str
    performance_threshold: float = 0.8
    sample_size: int = 100


class CreateEmbeddingRefinementRequest(BaseModel):
    tenant_id: str
    similarity_threshold: float = 0.85
    batch_size: int = 1000


class TrainingFeedbackRequest(BaseModel):
    session_id: str
    feedback_type: str
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    actual_output: Dict[str, Any]
    quality_score: float
    tenant_id: str


@router.post("/ontology-loop")
async def create_ontology_training_loop(
    request: CreateOntologyTrainingRequest,
    llm_adapter=Depends(get_llm_adapter),
    message_bus=Depends(get_message_bus),
    tracer=Depends(get_tracer)
):
    """Create an ontology evolution training loop."""
    
    try:
        use_case = CreateAdaptiveTrainingLoopUseCase(
            llm_adapter=llm_adapter,
            message_bus=message_bus,
            tracer=tracer
        )
        
        loop_id = await use_case.create_ontology_training_loop(
            kg_id=request.kg_id,
            tenant_id=request.tenant_id,
            feedback_threshold=request.feedback_threshold,
            retraining_interval_hours=request.retraining_interval_hours
        )
        
        return {
            "loop_id": loop_id,
            "type": "ontology_evolution",
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create ontology training loop: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query-optimization-loop")
async def create_query_optimization_loop(
    request: CreateQueryOptimizationRequest,
    llm_adapter=Depends(get_llm_adapter),
    message_bus=Depends(get_message_bus),
    tracer=Depends(get_tracer)
):
    """Create a query optimization training loop."""
    
    try:
        use_case = CreateAdaptiveTrainingLoopUseCase(
            llm_adapter=llm_adapter,
            message_bus=message_bus,
            tracer=tracer
        )
        
        loop_id = await use_case.create_query_optimization_loop(
            tenant_id=request.tenant_id,
            performance_threshold=request.performance_threshold,
            sample_size=request.sample_size
        )
        
        return {
            "loop_id": loop_id,
            "type": "query_optimization",
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create query optimization loop: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embedding-refinement-loop")
async def create_embedding_refinement_loop(
    request: CreateEmbeddingRefinementRequest,
    llm_adapter=Depends(get_llm_adapter),
    message_bus=Depends(get_message_bus),
    tracer=Depends(get_tracer)
):
    """Create an embedding refinement training loop."""
    
    try:
        use_case = CreateAdaptiveTrainingLoopUseCase(
            llm_adapter=llm_adapter,
            message_bus=message_bus,
            tracer=tracer
        )
        
        loop_id = await use_case.create_embedding_refinement_loop(
            tenant_id=request.tenant_id,
            similarity_threshold=request.similarity_threshold,
            batch_size=request.batch_size
        )
        
        return {
            "loop_id": loop_id,
            "type": "embedding_refinement",
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create embedding refinement loop: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def submit_training_feedback(
    request: TrainingFeedbackRequest,
    background_tasks: BackgroundTasks,
    llm_adapter=Depends(get_llm_adapter),
    message_bus=Depends(get_message_bus),
    tracer=Depends(get_tracer)
):
    """Submit training feedback for continuous improvement."""
    
    try:
        use_case = CreateAdaptiveTrainingLoopUseCase(
            llm_adapter=llm_adapter,
            message_bus=message_bus,
            tracer=tracer
        )
        
        # Submit feedback asynchronously
        background_tasks.add_task(
            use_case.submit_training_feedback,
            session_id=request.session_id,
            feedback_type=request.feedback_type,
            input_data=request.input_data,
            expected_output=request.expected_output,
            actual_output=request.actual_output,
            quality_score=request.quality_score,
            tenant_id=request.tenant_id
        )
        
        return {"status": "feedback_submitted"}
        
    except Exception as e:
        logger.error(f"Failed to submit training feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{tenant_id}")
async def get_training_status(
    tenant_id: str,
    llm_adapter=Depends(get_llm_adapter),
    message_bus=Depends(get_message_bus),
    tracer=Depends(get_tracer)
):
    """Get status of all training loops for a tenant."""
    
    try:
        use_case = CreateAdaptiveTrainingLoopUseCase(
            llm_adapter=llm_adapter,
            message_bus=message_bus,
            tracer=tracer
        )
        
        status = use_case.get_training_loops_status(tenant_id)
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get training status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/loop/{loop_id}")
async def stop_training_loop(
    loop_id: str,
    llm_adapter=Depends(get_llm_adapter),
    message_bus=Depends(get_message_bus),
    tracer=Depends(get_tracer)
):
    """Stop a specific training loop."""
    
    try:
        use_case = CreateAdaptiveTrainingLoopUseCase(
            llm_adapter=llm_adapter,
            message_bus=message_bus,
            tracer=tracer
        )
        
        await use_case.stop_training_loop(loop_id)
        
        return {
            "loop_id": loop_id,
            "status": "stopped"
        }
        
    except Exception as e:
        logger.error(f"Failed to stop training loop: {e}")
        raise HTTPException(status_code=500, detail=str(e))
