import os
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient

from analytics import aggregate_revenue
from ui_adapters.rest_api.routes import analytics as analytics_routes


def _setup_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE billing_events (occurred_at TEXT, account_id TEXT, event_type TEXT, amount REAL)"
    )
    cur.execute("CREATE TABLE segment_sales (occurred_at TEXT, amount REAL)")
    cur.execute(
        "CREATE TABLE bid_optimization_charges (occurred_at TEXT, amount REAL)"
    )
    # sample data for January 2024
    cur.executemany(
        "INSERT INTO billing_events VALUES (?,?,?,?)",
        [
            ("2024-01-15", "acct1", "subscription", 100),
            ("2024-01-20", "acct2", "subscription", 150),
            ("2024-01-25", "acct1", "churn", 0),
        ],
    )
    cur.executemany(
        "INSERT INTO segment_sales VALUES (?,?)",
        [("2024-01-10", 200)],
    )
    cur.executemany(
        "INSERT INTO bid_optimization_charges VALUES (?,?)",
        [("2024-01-05", 50)],
    )
    conn.commit()
    return conn


def test_aggregate_revenue(tmp_path):
    db_path = tmp_path / "rev.db"
    conn = _setup_db(str(db_path))
    aggregate_revenue(conn)
    cur = conn.cursor()
    cur.execute("SELECT period, mrr, arpu, churn FROM revenue_analytics")
    rows = cur.fetchall()
    assert rows == [("2024-01-01", 500.0, 250.0, 0.5)]
    conn.close()


def test_revenue_endpoint(tmp_path):
    db_path = tmp_path / "rev.db"
    _setup_db(str(db_path)).close()
    os.environ["ANALYTICS_DB_URL"] = str(db_path)
    app = FastAPI()
    app.include_router(analytics_routes.router)
    with TestClient(app) as client:
        resp = client.get("/api/v1/analytics/revenue")
        assert resp.status_code == 200
        data = resp.json()["revenue"]
        assert data[0]["mrr"] == 500.0
        assert data[0]["arpu"] == 250.0
        assert data[0]["churn"] == 0.5
