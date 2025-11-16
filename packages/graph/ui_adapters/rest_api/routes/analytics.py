"""Analytics endpoints for internal dashboards."""

from __future__ import annotations

import os
import sqlite3
from fastapi import APIRouter, HTTPException

try:  # pragma: no cover - support both package layouts
    from services.graph.analytics import aggregate_revenue
except ModuleNotFoundError:  # pragma: no cover
    from analytics import aggregate_revenue

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


def _connect() -> sqlite3.Connection:
    db_path = os.environ.get("ANALYTICS_DB_URL", "analytics.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/revenue")
def get_revenue_metrics():
    """Return aggregated revenue metrics for dashboards."""
    try:
        conn = _connect()
        aggregate_revenue(conn)
        cur = conn.cursor()
        cur.execute(
            "SELECT period, mrr, arpu, churn FROM revenue_analytics ORDER BY period"
        )
        rows = [dict(row) for row in cur.fetchall()]
        conn.close()
        return {"revenue": rows}
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=str(exc))
