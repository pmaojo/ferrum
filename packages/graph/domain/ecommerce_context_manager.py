from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from abc import ABC, abstractmethod

from domain.entities import ScientificDomain
from application.ports.graph import GraphRetrieverPort
from application.ports.multimodal import ImageEmbeddingPort, AudioEmbeddingPort
from application.ports.base import TracingPort, CachePort


@dataclass
class CustomerContext:
    """Unified customer context across all touchpoints."""
    customer_id: str
    tenant_id: str
    intent_signals: List[str]
    purchase_history: List[Dict[str, Any]]
    interaction_timeline: List[Dict[str, Any]]
    current_session: Dict[str, Any]
    predicted_interests: List[str]
    segment_memberships: List[str]
    lifetime_value: float
    last_updated: datetime


@dataclass
class CampaignContext:
    """Campaign and creative context for optimization."""
    campaign_id: str
    tenant_id: str
    creative_assets: List[Dict[str, Any]]
    performance_metrics: Dict[str, float]
    target_segments: List[str]
    bid_history: List[Dict[str, Any]]
    optimization_rules: List[Dict[str, Any]]
    current_budget: float
    last_updated: datetime


@dataclass
class BidRequestContext:
    """Real-time context for DSP bid decisions."""
    bid_request_id: str
    customer_context: CustomerContext
    campaign_context: CampaignContext
    creative_match_score: float
    intent_alignment_score: float
    predicted_ctr: float
    predicted_conversion: float
    recommended_bid: float
    confidence_score: float


class ContextManagerPort(ABC):
    """Port for context management operations."""

    @abstractmethod
    async def track_customer_event(self, tenant_id: str, customer_id: str, event: Dict[str, Any]) -> None:
        """Track a customer interaction event."""
        pass

    @abstractmethod
    async def get_customer_context(self, tenant_id: str, customer_id: str) -> Optional[CustomerContext]:
        """Retrieve unified customer context."""
        pass

    @abstractmethod
    async def optimize_bid_request(self, tenant_id: str, bid_request: Dict[str, Any]) -> BidRequestContext:
        """Generate optimized bid context for real-time bidding."""
        pass


class EcommerceContextManager:
    """Core domain service for managing unified customer and campaign context."""

    def __init__(
        self,
        graph_port: GraphRetrieverPort,
        image_embedding_port: ImageEmbeddingPort,
        audio_embedding_port: AudioEmbeddingPort,
        cache_port: CachePort,
        tracer: TracingPort,
    ):
        self.graph_port = graph_port
        self.image_embedding_port = image_embedding_port
        self.audio_embedding_port = audio_embedding_port
        self.cache_port = cache_port
        self.tracer = tracer

    async def process_ecommerce_event(
        self, 
        tenant_id: str, 
        customer_id: str, 
        event_type: str,
        event_data: Dict[str, Any]
    ) -> CustomerContext:
        """Process e-commerce events and update customer context."""

        # Record event in knowledge graph
        triples = [
            (f"customer:{customer_id}", "performed", f"event:{event_type}"),
            (f"event:{event_type}", "occurred_at", str(datetime.utcnow())),
            (f"event:{event_type}", "has_data", str(event_data)),
        ]

        if event_type == "product_view":
            product_id = event_data.get("product_id")
            triples.extend([
                (f"customer:{customer_id}", "viewed", f"product:{product_id}"),
                (f"product:{product_id}", "viewed_by", f"customer:{customer_id}"),
            ])
        elif event_type == "purchase":
            for item in event_data.get("items", []):
                product_id = item.get("product_id")
                triples.extend([
                    (f"customer:{customer_id}", "purchased", f"product:{product_id}"),
                    (f"product:{product_id}", "purchased_by", f"customer:{customer_id}"),
                ])

        # Store in graph
        await self.graph_port.store_triples(triples, tenant_id, f"ecommerce_context_{customer_id}")

        # Update customer context
        return await self._build_customer_context(tenant_id, customer_id)

    async def process_advertising_event(
        self,
        tenant_id: str,
        customer_id: str,
        campaign_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> CustomerContext:
        """Process advertising events (impressions, clicks, conversions)."""

        triples = [
            (f"customer:{customer_id}", f"advertising_{event_type}", f"campaign:{campaign_id}"),
            (f"campaign:{campaign_id}", f"generated_{event_type}", f"customer:{customer_id}"),
        ]

        if event_type == "impression":
            creative_id = event_data.get("creative_id")
            triples.extend([
                (f"customer:{customer_id}", "saw_creative", f"creative:{creative_id}"),
                (f"creative:{creative_id}", "shown_to", f"customer:{customer_id}"),
            ])
        elif event_type == "click":
            triples.append((f"customer:{customer_id}", "clicked", f"campaign:{campaign_id}"))
        elif event_type == "conversion":
            conversion_value = event_data.get("value", 0)
            triples.extend([
                (f"customer:{customer_id}", "converted_from", f"campaign:{campaign_id}"),
                (f"campaign:{campaign_id}", "generated_conversion", str(conversion_value)),
            ])

        await self.graph_port.store_triples(triples, tenant_id, f"advertising_context_{customer_id}")
        return await self._build_customer_context(tenant_id, customer_id)

    async def optimize_dsp_bid(
        self,
        tenant_id: str,
        bid_request: Dict[str, Any],
        timeout_ms: int = 100
    ) -> BidRequestContext:
        """Generate real-time bid optimization context for DSP."""

        start_time = datetime.utcnow()
        customer_id = bid_request.get("user_id")
        campaign_id = bid_request.get("campaign_id")

        # Retrieve customer and campaign context in parallel
        customer_context = await self._build_customer_context(tenant_id, customer_id)
        campaign_context = await self._build_campaign_context(tenant_id, campaign_id)

        # Analyze creative assets if available
        creative_match_score = 0.0
        if "creative_assets" in bid_request:
            creative_match_score = await self._analyze_creative_match(
                customer_context, bid_request["creative_assets"]
            )

        # Calculate intent alignment
        intent_alignment_score = await self._calculate_intent_alignment(
            customer_context, campaign_context
        )

        # Predict performance metrics
        predicted_ctr = await self._predict_ctr(customer_context, campaign_context)
        predicted_conversion = await self._predict_conversion(customer_context, campaign_context)

        # Calculate recommended bid
        base_bid = campaign_context.optimization_rules[0].get("base_bid", 1.0)
        recommended_bid = base_bid * creative_match_score * intent_alignment_score * predicted_ctr

        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        confidence_score = min(creative_match_score, intent_alignment_score, predicted_ctr)

        # Record metrics
        self.tracer.record_metric(
            "dsp_bid_optimization_time_ms", 
            processing_time, 
            tenant_id=tenant_id,
            campaign_id=campaign_id
        )

        return BidRequestContext(
            bid_request_id=bid_request.get("id", ""),
            customer_context=customer_context,
            campaign_context=campaign_context,
            creative_match_score=creative_match_score,
            intent_alignment_score=intent_alignment_score,
            predicted_ctr=predicted_ctr,
            predicted_conversion=predicted_conversion,
            recommended_bid=recommended_bid,
            confidence_score=confidence_score
        )

    async def _build_customer_context(self, tenant_id: str, customer_id: str) -> CustomerContext:
        """Build unified customer context from knowledge graph."""

        # Query customer interactions
        query = f"""
        MATCH (c:Customer {{id: '{customer_id}'}})
        OPTIONAL MATCH (c)-[r]->(entity)
        RETURN c, type(r) as relationship, entity
        LIMIT 100
        """

        results = await self.graph_port.execute_query(query, tenant_id, f"context_{customer_id}")

        # Extract context from results
        intent_signals = []
        purchase_history = []
        interaction_timeline = []

        for result in results:
            relationship = result.get("relationship", "")
            entity = result.get("entity", {})

            if relationship == "purchased":
                purchase_history.append(entity)
            elif relationship == "viewed":
                intent_signals.append(f"interested_in_{entity.get('category', 'unknown')}")
            elif relationship == "clicked":
                intent_signals.append(f"engaged_with_{entity.get('type', 'unknown')}")

        return CustomerContext(
            customer_id=customer_id,
            tenant_id=tenant_id,
            intent_signals=list(set(intent_signals)),
            purchase_history=purchase_history,
            interaction_timeline=interaction_timeline,
            current_session={},
            predicted_interests=[],
            segment_memberships=[],
            lifetime_value=0.0,
            last_updated=datetime.utcnow()
        )

    async def _build_campaign_context(self, tenant_id: str, campaign_id: str) -> CampaignContext:
        """Build campaign context from knowledge graph."""

        query = f"""
        MATCH (cam:Campaign {{id: '{campaign_id}'}})
        OPTIONAL MATCH (cam)-[r]->(entity)
        RETURN cam, type(r) as relationship, entity
        """

        results = await self.graph_port.execute_query(query, tenant_id, f"campaign_{campaign_id}")

        creative_assets = []
        performance_metrics = {}

        for result in results:
            relationship = result.get("relationship", "")
            entity = result.get("entity", {})

            if relationship == "has_creative":
                creative_assets.append(entity)
            elif relationship == "has_performance":
                performance_metrics.update(entity)

        return CampaignContext(
            campaign_id=campaign_id,
            tenant_id=tenant_id,
            creative_assets=creative_assets,
            performance_metrics=performance_metrics,
            target_segments=[],
            bid_history=[],
            optimization_rules=[{"base_bid": 1.0}],
            current_budget=1000.0,
            last_updated=datetime.utcnow()
        )

    async def get_campaign_metrics(self, tenant_id: str, campaign_id: str) -> Dict[str, Any]:
        """Aggregate advertising events for a campaign."""

        query = f"""
        MATCH (c:Campaign {{id: '{campaign_id}'}})-[r]->(e)
        WHERE type(r) IN ['generated_impression','generated_click','generated_conversion']
        RETURN type(r) as event_type, count(*) as count, sum(toFloat(e)) as value
        """

        results = await self.graph_port.execute_query(query, tenant_id, f"campaign_{campaign_id}")

        metrics = {"impressions": 0, "clicks": 0, "conversions": 0, "spend": 0.0}
        for row in results:
            event = row.get("event_type")
            count = int(row.get("count", 0))
            if event == "generated_impression":
                metrics["impressions"] = count
            elif event == "generated_click":
                metrics["clicks"] = count
            elif event == "generated_conversion":
                metrics["conversions"] = count
                metrics["spend"] = float(row.get("value", 0.0) or 0.0)

        return metrics

    async def _analyze_creative_match(
        self,
        customer_context: CustomerContext,
        creative_assets: List[Dict[str, Any]]
    ) -> float:
        """Analyze how well creative assets match customer preferences."""

        if not creative_assets or not customer_context.intent_signals:
            return 0.5  # Neutral score

        # Simple matching based on intent signals
        matches = 0
        for asset in creative_assets:
            asset_keywords = asset.get("keywords", [])
            for signal in customer_context.intent_signals:
                if any(keyword in signal for keyword in asset_keywords):
                    matches += 1

        return min(matches / len(creative_assets), 1.0)

    async def _calculate_intent_alignment(
        self, 
        customer_context: CustomerContext, 
        campaign_context: CampaignContext
    ) -> float:
        """Calculate how well campaign aligns with customer intent."""

        if not customer_context.intent_signals:
            return 0.5

        # Simple alignment scoring
        alignment_score = 0.0
        for creative in campaign_context.creative_assets:
            creative_category = creative.get("category", "")
            for signal in customer_context.intent_signals:
                if creative_category in signal:
                    alignment_score += 0.1

        return min(alignment_score, 1.0)

    async def _predict_ctr(
        self, 
        customer_context: CustomerContext, 
        campaign_context: CampaignContext
    ) -> float:
        """Predict click-through rate based on context."""

        base_ctr = 0.02  # 2% baseline

        # Boost based on purchase history
        if customer_context.purchase_history:
            base_ctr *= 1.5

        # Boost based on recent interactions
        if customer_context.intent_signals:
            base_ctr *= 1.2

        return min(base_ctr, 0.15)  # Cap at 15%

    async def _predict_conversion(
        self, 
        customer_context: CustomerContext, 
        campaign_context: CampaignContext
    ) -> float:
        """Predict conversion probability."""

        base_conversion = 0.01  # 1% baseline

        # Higher conversion for existing customers
        if customer_context.purchase_history:
            base_conversion *= 3.0

        # Boost for high-intent signals
        high_intent_signals = [s for s in customer_context.intent_signals if "purchase" in s or "buy" in s]
        if high_intent_signals:
            base_conversion *= 2.0

        return min(base_conversion, 0.20)  # Cap at 20%
