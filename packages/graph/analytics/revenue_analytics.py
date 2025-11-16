"""Revenue analytics aggregation utilities."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable

import sqlite3


@dataclass
class RevenueRecord:
    """Aggregated revenue metrics for a period."""

    period: str
    mrr: float
    arpu: float
    churn: float


def _month_key(ts: str) -> str:
    dt = datetime.fromisoformat(ts)
    return dt.strftime("%Y-%m-01")


def aggregate_revenue(conn: sqlite3.Connection) -> None:
    """Aggregate billing, sales and bid charges into revenue_analytics table.

    Parameters
    ----------
    conn:
        Database connection. Tables ``billing_events``, ``segment_sales`` and
        ``bid_optimization_charges`` must exist. The result will be stored in
        ``revenue_analytics``.
    """

    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS revenue_analytics (
            period TEXT PRIMARY KEY,
            mrr REAL NOT NULL,
            arpu REAL NOT NULL,
            churn REAL NOT NULL
        )
        """
    )

    cur.execute("DELETE FROM revenue_analytics")

    aggregates: Dict[str, Dict[str, object]] = defaultdict(
        lambda: {"billing": 0.0, "segment": 0.0, "bid": 0.0, "accounts": set(), "churned": 0}
    )

    for occurred_at, account_id, event_type, amount in cur.execute(
        "SELECT occurred_at, account_id, event_type, amount FROM billing_events"
    ):
        key = _month_key(occurred_at)
        data = aggregates[key]
        data["billing"] += float(amount)
        data["accounts"].add(account_id)
        if event_type == "churn":
            data["churned"] += 1

    for occurred_at, amount in cur.execute(
        "SELECT occurred_at, amount FROM segment_sales"
    ):
        key = _month_key(occurred_at)
        aggregates[key]["segment"] += float(amount)

    for occurred_at, amount in cur.execute(
        "SELECT occurred_at, amount FROM bid_optimization_charges"
    ):
        key = _month_key(occurred_at)
        aggregates[key]["bid"] += float(amount)

    records: Iterable[RevenueRecord] = []
    for period, data in sorted(aggregates.items()):
        total_revenue = data["billing"] + data["segment"] + data["bid"]
        account_count = max(len(data["accounts"]), 1)
        churn_rate = data["churned"] / account_count
        records = list(records) + [
            RevenueRecord(
                period=period,
                mrr=total_revenue,
                arpu=total_revenue / account_count,
                churn=churn_rate,
            )
        ]

    cur.executemany(
        "INSERT INTO revenue_analytics(period, mrr, arpu, churn) VALUES (?, ?, ?, ?)",
        [(r.period, r.mrr, r.arpu, r.churn) for r in records],
    )
    conn.commit()
