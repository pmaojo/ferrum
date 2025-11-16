-- Schema for revenue analytics aggregation
CREATE TABLE IF NOT EXISTS billing_events (
    occurred_at TIMESTAMP NOT NULL,
    account_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    amount NUMERIC NOT NULL
);

CREATE TABLE IF NOT EXISTS segment_sales (
    occurred_at TIMESTAMP NOT NULL,
    amount NUMERIC NOT NULL
);

CREATE TABLE IF NOT EXISTS bid_optimization_charges (
    occurred_at TIMESTAMP NOT NULL,
    amount NUMERIC NOT NULL
);

CREATE TABLE IF NOT EXISTS revenue_analytics (
    period DATE PRIMARY KEY,
    mrr NUMERIC NOT NULL,
    arpu NUMERIC NOT NULL,
    churn NUMERIC NOT NULL
);
