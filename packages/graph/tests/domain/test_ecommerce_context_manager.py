import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from domain.ecommerce_context_manager import (
    EcommerceContextManager,
    CustomerContext,
    CampaignContext,
)


@pytest.fixture
def graph_port():
    port = AsyncMock()
    port.store_triples = AsyncMock()
    port.execute_query = AsyncMock()
    return port


@pytest.fixture
def tracer():
    tracer = Mock()
    tracer.record_metric = Mock()
    return tracer


@pytest.fixture
def context_manager(graph_port, tracer):
    return EcommerceContextManager(
        graph_port=graph_port,
        image_embedding_port=AsyncMock(),
        audio_embedding_port=AsyncMock(),
        cache_port=AsyncMock(),
        tracer=tracer,
    )


@pytest.mark.asyncio
async def test_process_ecommerce_event(context_manager, graph_port):
    graph_port.execute_query.return_value = [
        {"relationship": "viewed", "entity": {"category": "electronics"}},
        {"relationship": "purchased", "entity": {"id": "p1"}},
    ]

    result = await context_manager.process_ecommerce_event(
        tenant_id="t1",
        customer_id="c1",
        event_type="product_view",
        event_data={"product_id": "p99"},
    )

    graph_port.store_triples.assert_awaited_once()
    triples, tenant, kg_id = graph_port.store_triples.call_args.args
    assert tenant == "t1"
    assert kg_id == "ecommerce_context_c1"
    assert ("customer:c1", "viewed", "product:p99") in triples
    graph_port.execute_query.assert_awaited_once()
    assert result.customer_id == "c1"
    assert set(result.intent_signals) == {"interested_in_electronics"}
    assert result.purchase_history == [{"id": "p1"}]


@pytest.mark.asyncio
async def test_process_advertising_event(context_manager, graph_port):
    graph_port.execute_query.return_value = [
        {"relationship": "clicked", "entity": {"type": "ad"}},
    ]

    result = await context_manager.process_advertising_event(
        tenant_id="t1",
        customer_id="c1",
        campaign_id="cmp1",
        event_type="click",
        event_data={},
    )

    graph_port.store_triples.assert_awaited_once()
    triples, tenant, kg_id = graph_port.store_triples.call_args.args
    assert tenant == "t1"
    assert kg_id == "advertising_context_c1"
    assert ("customer:c1", "clicked", "campaign:cmp1") in triples
    assert set(result.intent_signals) == {"engaged_with_ad"}


@pytest.mark.asyncio
async def test_build_customer_context_parses_results(context_manager, graph_port):
    graph_port.execute_query.return_value = [
        {"relationship": "purchased", "entity": {"id": "p1"}},
        {"relationship": "viewed", "entity": {"category": "books"}},
        {"relationship": "clicked", "entity": {"type": "ad"}},
    ]

    ctx = await context_manager._build_customer_context("t1", "c1")

    graph_port.execute_query.assert_awaited_once()
    assert ctx.purchase_history == [{"id": "p1"}]
    assert set(ctx.intent_signals) == {"interested_in_books", "engaged_with_ad"}


@pytest.mark.asyncio
async def test_build_campaign_context_parses_results(context_manager, graph_port):
    graph_port.execute_query.return_value = [
        {"relationship": "has_creative", "entity": {"id": "cr1"}},
        {"relationship": "has_performance", "entity": {"ctr": 0.1}},
    ]

    ctx = await context_manager._build_campaign_context("t1", "cmp1")

    graph_port.execute_query.assert_awaited_once()
    assert ctx.creative_assets == [{"id": "cr1"}]
    assert ctx.performance_metrics == {"ctr": 0.1}


@pytest.mark.asyncio
async def test_optimize_dsp_bid(context_manager, monkeypatch):
    customer = CustomerContext(
        customer_id="c1",
        tenant_id="t1",
        intent_signals=["sig"],
        purchase_history=[],
        interaction_timeline=[],
        current_session={},
        predicted_interests=[],
        segment_memberships=[],
        lifetime_value=0.0,
        last_updated=datetime.utcnow(),
    )

    campaign = CampaignContext(
        campaign_id="cmp1",
        tenant_id="t1",
        creative_assets=[{"category": "sig"}],
        performance_metrics={},
        target_segments=[],
        bid_history=[],
        optimization_rules=[{"base_bid": 2.0}],
        current_budget=1000.0,
        last_updated=datetime.utcnow(),
    )

    monkeypatch.setattr(
        context_manager,
        "_build_customer_context",
        AsyncMock(return_value=customer),
    )
    monkeypatch.setattr(
        context_manager,
        "_build_campaign_context",
        AsyncMock(return_value=campaign),
    )
    monkeypatch.setattr(
        context_manager,
        "_analyze_creative_match",
        AsyncMock(return_value=0.8),
    )
    monkeypatch.setattr(
        context_manager,
        "_calculate_intent_alignment",
        AsyncMock(return_value=0.7),
    )
    monkeypatch.setattr(
        context_manager,
        "_predict_ctr",
        AsyncMock(return_value=0.1),
    )
    monkeypatch.setattr(
        context_manager,
        "_predict_conversion",
        AsyncMock(return_value=0.05),
    )

    bid_request = {
        "id": "b1",
        "user_id": "c1",
        "campaign_id": "cmp1",
        "creative_assets": [{}],
    }

    result = await context_manager.optimize_dsp_bid("t1", bid_request)

    expected_bid = 2.0 * 0.8 * 0.7 * 0.1
    assert pytest.approx(result.recommended_bid) == expected_bid
    assert result.bid_request_id == "b1"
    context_manager.tracer.record_metric.assert_called_once()
