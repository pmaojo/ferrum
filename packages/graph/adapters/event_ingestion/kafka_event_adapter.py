import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict

from application.ports.base import TracingPort
from domain.ecommerce_context_manager import EcommerceContextManager
from jsonschema import ValidationError, validate


class KafkaEventAdapter:
    """Adapter for ingesting events from Kafka for real-time context tracking."""

    def __init__(
        self,
        context_manager: EcommerceContextManager,
        tracer: TracingPort,
        bootstrap_servers: str = "localhost:9092",
    ):
        self.context_manager = context_manager
        self.tracer = tracer
        self.bootstrap_servers = bootstrap_servers
        self.logger = logging.getLogger(__name__)

        # Event handlers mapping
        self.event_handlers = {
            "ecommerce.product.view": self._handle_product_view,
            "ecommerce.cart.add": self._handle_cart_add,
            "ecommerce.purchase": self._handle_purchase,
            "advertising.impression": self._handle_impression,
            "advertising.click": self._handle_click,
            "advertising.conversion": self._handle_conversion,
            "dsp.bid.request": self._handle_bid_request,
            "dsp.bid.response": self._handle_bid_response,
        }

        # JSON schemas for event validation
        self.event_schemas: Dict[str, Dict[str, Any]] = {
            "ecommerce.product.view": {
                "type": "object",
                "properties": {
                    "event_type": {"type": "string"},
                    "tenant_id": {"type": "string"},
                    "customer_id": {"type": "string"},
                    "product_id": {"type": "string"},
                },
                "required": [
                    "event_type",
                    "tenant_id",
                    "customer_id",
                    "product_id",
                ],
            },
            "ecommerce.cart.add": {
                "type": "object",
                "properties": {
                    "event_type": {"type": "string"},
                    "tenant_id": {"type": "string"},
                    "customer_id": {"type": "string"},
                    "product_id": {"type": "string"},
                    "quantity": {"type": ["number", "string"]},
                },
                "required": [
                    "event_type",
                    "tenant_id",
                    "customer_id",
                    "product_id",
                    "quantity",
                ],
            },
            "ecommerce.purchase": {
                "type": "object",
                "properties": {
                    "event_type": {"type": "string"},
                    "tenant_id": {"type": "string"},
                    "customer_id": {"type": "string"},
                    "transaction_id": {"type": "string"},
                    "items": {"type": "array"},
                },
                "required": [
                    "event_type",
                    "tenant_id",
                    "customer_id",
                    "transaction_id",
                    "items",
                ],
            },
            "advertising.impression": {
                "type": "object",
                "properties": {
                    "event_type": {"type": "string"},
                    "tenant_id": {"type": "string"},
                    "customer_id": {"type": "string"},
                    "campaign_id": {"type": "string"},
                    "creative_id": {"type": "string"},
                },
                "required": [
                    "event_type",
                    "tenant_id",
                    "customer_id",
                    "campaign_id",
                    "creative_id",
                ],
            },
            "advertising.click": {
                "type": "object",
                "properties": {
                    "event_type": {"type": "string"},
                    "tenant_id": {"type": "string"},
                    "customer_id": {"type": "string"},
                    "campaign_id": {"type": "string"},
                    "creative_id": {"type": "string"},
                    "click_url": {"type": "string"},
                },
                "required": [
                    "event_type",
                    "tenant_id",
                    "customer_id",
                    "campaign_id",
                    "creative_id",
                    "click_url",
                ],
            },
            "advertising.conversion": {
                "type": "object",
                "properties": {
                    "event_type": {"type": "string"},
                    "tenant_id": {"type": "string"},
                    "customer_id": {"type": "string"},
                    "campaign_id": {"type": "string"},
                    "conversion_type": {"type": "string"},
                },
                "required": [
                    "event_type",
                    "tenant_id",
                    "customer_id",
                    "campaign_id",
                    "conversion_type",
                ],
            },
            "dsp.bid.request": {
                "type": "object",
                "properties": {
                    "event_type": {"type": "string"},
                    "tenant_id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "campaign_id": {"type": "string"},
                },
                "required": [
                    "event_type",
                    "tenant_id",
                    "user_id",
                    "campaign_id",
                ],
            },
            "dsp.bid.response": {
                "type": "object",
                "properties": {
                    "event_type": {"type": "string"},
                    "tenant_id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "bid_won": {"type": ["boolean", "number", "string"]},
                    "winning_price": {"type": ["number", "string"]},
                },
                "required": [
                    "event_type",
                    "tenant_id",
                    "user_id",
                    "bid_won",
                    "winning_price",
                ],
            },
        }

        self.deadletter_topic = "advertising.deadletter"
        self._producer = None

    def _get_producer(self):
        if self._producer is None:
            try:
                from kafka import KafkaProducer

                self._producer = KafkaProducer(
                    bootstrap_servers=[self.bootstrap_servers],
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                )
            except ImportError:
                self.logger.warning(
                    "kafka-python3 not available, dead-letter events will not be published"
                )
                self._producer = None
        return self._producer

    def _publish_deadletter(self, payload: Dict[str, Any]) -> None:
        producer = self._get_producer()
        if producer:
            producer.send(self.deadletter_topic, payload)

    async def start_consuming(self, topics: list[str]) -> None:
        """Start consuming events from Kafka topics."""
        try:
            # Import kafka-python3 if available, otherwise use mock
            try:
                from kafka import KafkaConsumer

                consumer = KafkaConsumer(
                    *topics,
                    bootstrap_servers=[self.bootstrap_servers],
                    auto_offset_reset="latest",
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    group_id="graphrag_context_manager",
                )

                self.logger.info(f"Started Kafka consumer for topics: {topics}")

                for message in consumer:
                    await self._process_event(message.topic, message.value)

            except ImportError:
                self.logger.warning(
                    "kafka-python3 not available, using mock event processing"
                )
                await self._mock_event_processing()

        except Exception as e:
            self.logger.error(f"Error in Kafka consumer: {e}")
            self.tracer.record_metric("kafka_consumer_errors", 1)

    async def _process_event(self, topic: str, event_data: Dict[str, Any]) -> None:
        """Process a single event from Kafka."""
        try:
            event_type = event_data.get("event_type", topic)
            tenant_id = event_data.get("tenant_id", "default")

            schema = self.event_schemas.get(event_type)
            if schema:
                try:
                    validate(event_data, schema)
                except ValidationError as e:
                    self.logger.warning(
                        f"Invalid event {event_type}: {e.message}"
                    )
                    self.tracer.record_metric(
                        "invalid_events",
                        1,
                        tenant_id=tenant_id,
                        event_type=event_type,
                    )
                    if event_type.startswith("advertising."):
                        self._publish_deadletter(event_data)
                        self.tracer.record_metric(
                            "deadlettered_events",
                            1,
                            tenant_id=tenant_id,
                            event_type=event_type,
                        )
                    return

            customer_id = event_data.get("customer_id") or event_data.get("user_id")

            if not customer_id:
                self.logger.warning(f"Event missing customer_id: {event_data}")
                return

            # Record event processing
            self.tracer.record_metric(
                "events_processed", 1, tenant_id=tenant_id, event_type=event_type
            )

            # Route to appropriate handler
            handler = self.event_handlers.get(event_type, self._handle_generic_event)
            await handler(tenant_id, customer_id, event_data)

        except Exception as e:
            self.logger.error(f"Error processing event: {e}")
            self.tracer.record_metric("event_processing_errors", 1)

    async def _handle_product_view(
        self, tenant_id: str, customer_id: str, event_data: Dict[str, Any]
    ) -> None:
        """Handle product view events."""
        await self.context_manager.process_ecommerce_event(
            tenant_id=tenant_id,
            customer_id=customer_id,
            event_type="product_view",
            event_data={
                "product_id": event_data.get("product_id"),
                "product_category": event_data.get("product_category"),
                "page_url": event_data.get("page_url"),
                "timestamp": event_data.get("timestamp", datetime.utcnow().isoformat()),
            },
        )

    async def _handle_cart_add(
        self, tenant_id: str, customer_id: str, event_data: Dict[str, Any]
    ) -> None:
        """Handle add to cart events."""
        await self.context_manager.process_ecommerce_event(
            tenant_id=tenant_id,
            customer_id=customer_id,
            event_type="cart_add",
            event_data={
                "product_id": event_data.get("product_id"),
                "quantity": event_data.get("quantity", 1),
                "price": event_data.get("price"),
                "timestamp": event_data.get("timestamp", datetime.utcnow().isoformat()),
            },
        )

    async def _handle_purchase(
        self, tenant_id: str, customer_id: str, event_data: Dict[str, Any]
    ) -> None:
        """Handle purchase events."""
        await self.context_manager.process_ecommerce_event(
            tenant_id=tenant_id,
            customer_id=customer_id,
            event_type="purchase",
            event_data={
                "transaction_id": event_data.get("transaction_id"),
                "items": event_data.get("items", []),
                "total_value": event_data.get("total_value"),
                "currency": event_data.get("currency", "USD"),
                "timestamp": event_data.get("timestamp", datetime.utcnow().isoformat()),
            },
        )

    async def _handle_impression(
        self, tenant_id: str, customer_id: str, event_data: Dict[str, Any]
    ) -> None:
        """Handle advertising impression events."""
        await self.context_manager.process_advertising_event(
            tenant_id=tenant_id,
            customer_id=customer_id,
            campaign_id=event_data.get("campaign_id"),
            event_type="impression",
            event_data={
                "creative_id": event_data.get("creative_id"),
                "placement": event_data.get("placement"),
                "timestamp": event_data.get("timestamp", datetime.utcnow().isoformat()),
            },
        )

    async def _handle_click(
        self, tenant_id: str, customer_id: str, event_data: Dict[str, Any]
    ) -> None:
        """Handle advertising click events."""
        await self.context_manager.process_advertising_event(
            tenant_id=tenant_id,
            customer_id=customer_id,
            campaign_id=event_data.get("campaign_id"),
            event_type="click",
            event_data={
                "creative_id": event_data.get("creative_id"),
                "click_url": event_data.get("click_url"),
                "timestamp": event_data.get("timestamp", datetime.utcnow().isoformat()),
            },
        )

    async def _handle_conversion(
        self, tenant_id: str, customer_id: str, event_data: Dict[str, Any]
    ) -> None:
        """Handle conversion events."""
        await self.context_manager.process_advertising_event(
            tenant_id=tenant_id,
            customer_id=customer_id,
            campaign_id=event_data.get("campaign_id"),
            event_type="conversion",
            event_data={
                "conversion_type": event_data.get("conversion_type"),
                "value": event_data.get("value"),
                "attribution_model": event_data.get("attribution_model", "last_click"),
                "timestamp": event_data.get("timestamp", datetime.utcnow().isoformat()),
            },
        )

    async def _handle_bid_request(
        self, tenant_id: str, customer_id: str, event_data: Dict[str, Any]
    ) -> None:
        """Handle DSP bid request events."""
        # Generate bid optimization context
        bid_context = await self.context_manager.optimize_dsp_bid(
            tenant_id=tenant_id, bid_request=event_data, timeout_ms=100
        )

        # Log bid optimization result
        self.logger.info(
            f"Optimized bid: {bid_context.recommended_bid} for customer {customer_id}"
        )

        self.tracer.record_metric(
            "bid_requests_optimized",
            1,
            tenant_id=tenant_id,
            confidence_score=bid_context.confidence_score,
        )

    async def _handle_bid_response(
        self, tenant_id: str, customer_id: str, event_data: Dict[str, Any]
    ) -> None:
        """Handle DSP bid response events."""
        # Track bid outcomes for learning
        bid_won = event_data.get("bid_won", False)
        winning_price = event_data.get("winning_price", 0.0)

        self.tracer.record_metric(
            "bid_responses",
            1,
            tenant_id=tenant_id,
            bid_won=bid_won,
            winning_price=winning_price,
        )

    async def _handle_generic_event(
        self, tenant_id: str, customer_id: str, event_data: Dict[str, Any]
    ) -> None:
        """Handle unknown event types."""
        self.logger.info(
            f"Processing generic event for customer {customer_id}: {event_data}"
        )

        # Store as generic interaction
        await self.context_manager.process_ecommerce_event(
            tenant_id=tenant_id,
            customer_id=customer_id,
            event_type="generic_interaction",
            event_data=event_data,
        )

    async def _mock_event_processing(self) -> None:
        """Mock event processing for development/demo purposes."""
        self.logger.info("Running mock event processing...")

        while True:
            # Simulate various events
            mock_events = [
                {
                    "event_type": "ecommerce.product.view",
                    "tenant_id": "demo_tenant",
                    "customer_id": "customer_123",
                    "product_id": "product_456",
                    "product_category": "electronics",
                    "timestamp": datetime.utcnow().isoformat(),
                },
                {
                    "event_type": "advertising.impression",
                    "tenant_id": "demo_tenant",
                    "customer_id": "customer_123",
                    "campaign_id": "campaign_789",
                    "creative_id": "creative_101",
                    "placement": "banner_top",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            ]

            for event in mock_events:
                await self._process_event(event["event_type"], event)

            await asyncio.sleep(10)  # Process mock events every 10 seconds
