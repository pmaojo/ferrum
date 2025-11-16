
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from domain.ecommerce_context_manager import BidRequestContext, EcommerceContextManager
from adapters.event_ingestion.kafka_event_adapter import KafkaEventAdapter
from ui_adapters.rest_api.dependencies import get_context_manager, get_event_adapter

logger = logging.getLogger(__name__)

BILLING_URL = os.getenv("BILLING_URL", "http://billing-service:8000")

router = APIRouter(prefix="/api/v1/ecommerce", tags=["E-commerce Context"])
security = HTTPBearer()


async def _emit_usage(tenant_id: str, feature: str, amount: int = 1) -> None:
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{BILLING_URL}/usage",
                json={"tenant_id": tenant_id, "feature": feature, "amount": amount},
                timeout=2.0,
            )
    except Exception as exc:  # pragma: no cover - best effort only
        logger.debug("Failed to emit usage metric: %s", exc)


class TrackEventRequest(BaseModel):
    """Request model for tracking customer events."""
    tenant_id: str
    customer_id: str
    event_type: str
    event_data: Dict[str, Any]


class BidOptimizationRequest(BaseModel):
    """Request model for DSP bid optimization."""
    tenant_id: str
    bid_request: Dict[str, Any]
    timeout_ms: int = 100


class CustomerContextResponse(BaseModel):
    """Response model for customer context."""
    customer_id: str
    tenant_id: str
    intent_signals: List[str]
    purchase_history: List[Dict[str, Any]]
    interaction_timeline: List[Dict[str, Any]]
    predicted_interests: List[str]
    segment_memberships: List[str]
    lifetime_value: float
    last_updated: datetime


class BidOptimizationResponse(BaseModel):
    """Response model for bid optimization."""
    bid_request_id: str
    recommended_bid: float
    creative_match_score: float
    intent_alignment_score: float
    predicted_ctr: float
    predicted_conversion: float
    confidence_score: float
    processing_time_ms: float


@router.post("/track-event")
async def track_customer_event(
    event: TrackEventRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    context_manager: EcommerceContextManager = Depends(get_context_manager),
):
    """Track customer interaction events for context building."""
    try:
        tenant_id = getattr(request.state, "tenant_id", None) if request else None
        if tenant_id != event.tenant_id:
            raise HTTPException(status_code=403, detail="Tenant mismatch")

        # Process event asynchronously
        background_tasks.add_task(
            _process_event_background,
            context_manager,
            event.tenant_id,
            event.customer_id,
            event.event_type,
            event.event_data,
            authenticated=True,
        )
        background_tasks.add_task(_emit_usage, event.tenant_id, "track-event")

        return {
            "success": True,
            "message": "Event queued for processing",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error tracking event: {str(e)}")


@router.get("/customer-context/{tenant_id}/{customer_id}")
async def get_customer_context(
    tenant_id: str,
    customer_id: str,
    context_manager: EcommerceContextManager = Depends(get_context_manager),
) -> CustomerContextResponse:
    """Retrieve unified customer context."""
    try:
        context = await context_manager._build_customer_context(tenant_id, customer_id)
        
        if not context:
            raise HTTPException(status_code=404, detail="Customer context not found")
        
        response = CustomerContextResponse(
            customer_id=context.customer_id,
            tenant_id=context.tenant_id,
            intent_signals=context.intent_signals,
            purchase_history=context.purchase_history,
            interaction_timeline=context.interaction_timeline,
            predicted_interests=context.predicted_interests,
            segment_memberships=context.segment_memberships,
            lifetime_value=context.lifetime_value,
            last_updated=context.last_updated
        )
        await _emit_usage(tenant_id, "get-customer-context")
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving context: {str(e)}")


@router.post("/optimize-bid")
async def optimize_dsp_bid(
    request: BidOptimizationRequest,
    context_manager: EcommerceContextManager = Depends(get_context_manager),
) -> BidOptimizationResponse:
    """Generate real-time bid optimization for DSP."""
    try:
        start_time = datetime.utcnow()
        
        bid_context = await context_manager.optimize_dsp_bid(
            tenant_id=request.tenant_id,
            bid_request=request.bid_request,
            timeout_ms=request.timeout_ms
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        response = BidOptimizationResponse(
            bid_request_id=bid_context.bid_request_id,
            recommended_bid=bid_context.recommended_bid,
            creative_match_score=bid_context.creative_match_score,
            intent_alignment_score=bid_context.intent_alignment_score,
            predicted_ctr=bid_context.predicted_ctr,
            predicted_conversion=bid_context.predicted_conversion,
            confidence_score=bid_context.confidence_score,
            processing_time_ms=processing_time
        )
        await _emit_usage(request.tenant_id, "optimize-bid")
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing bid: {str(e)}")


@router.post("/bulk-events")
async def track_bulk_events(
    events: List[TrackEventRequest],
    request: Request,
    background_tasks: BackgroundTasks,
    context_manager: EcommerceContextManager = Depends(get_context_manager),
):
    """Track multiple customer events in bulk."""
    try:
        tenant_id = getattr(request.state, "tenant_id", None)
        for event in events:
            if event.tenant_id != tenant_id:
                raise HTTPException(status_code=403, detail="Tenant mismatch")
            background_tasks.add_task(
                _process_event_background,
                context_manager,
                event.tenant_id,
                event.customer_id,
                event.event_type,
                event.event_data,
                authenticated=True,
            )

        background_tasks.add_task(
            _emit_usage, tenant_id, "bulk-events", len(events)
        )

        return {
            "success": True,
            "events_queued": len(events),
            "message": "Bulk events queued for processing",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing bulk events: {str(e)}")


@router.get("/analytics/{tenant_id}")
async def get_tenant_analytics(
    tenant_id: str,
    context_manager: EcommerceContextManager = Depends(get_context_manager),
):
    """Get analytics and insights for a tenant."""
    try:
        # Query aggregated data from knowledge graph
        query = f"""
        MATCH (c:Customer)-[r]->(entity)
        WHERE c.tenant_id = '{tenant_id}'
        RETURN 
            type(r) as interaction_type,
            count(r) as count,
            collect(DISTINCT c.id)[0..10] as sample_customers
        """
        
        results = await context_manager.graph_port.execute_query(
            query, tenant_id, f"analytics_{tenant_id}"
        )
        
        analytics = {}
        for result in results:
            interaction_type = result.get("interaction_type", "unknown")
            count = result.get("count", 0)
            analytics[interaction_type] = count
        
        result = {
            "tenant_id": tenant_id,
            "analytics": analytics,
            "timestamp": datetime.utcnow().isoformat()
        }
        await _emit_usage(tenant_id, "get-analytics")
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics: {str(e)}")


async def _process_event_background(
    context_manager: EcommerceContextManager,
    tenant_id: str,
    customer_id: str,
    event_type: str,
    event_data: Dict[str, Any],
    authenticated: bool = True,
):
    """Background task for processing events."""
    try:
        logger.info("Processing event '%s' for tenant %s", event_type, tenant_id)
        if event_type.startswith("advertising."):
            if not authenticated:
                logger.warning(
                    "Rejected unauthenticated advertising event for tenant %s",
                    tenant_id,
                )
                return
            campaign_id = event_data.get("campaign_id", "unknown")
            await context_manager.process_advertising_event(
                tenant_id=tenant_id,
                customer_id=customer_id,
                campaign_id=campaign_id,
                event_type=event_type.replace("advertising.", ""),
                event_data=event_data,
            )
        else:
            await context_manager.process_ecommerce_event(
                tenant_id=tenant_id,
                customer_id=customer_id,
                event_type=event_type.replace("ecommerce.", ""),
                event_data=event_data,
            )
    except Exception as e:
        # Log error but don't raise to avoid breaking background processing
        logger.error(
            "Error processing background event for tenant %s: %s", tenant_id, e
        )
