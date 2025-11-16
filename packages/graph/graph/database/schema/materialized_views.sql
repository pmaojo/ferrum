
-- Performance-focused Materialized Views

-- Tenant usage summary
CREATE MATERIALIZED VIEW tenant_usage_summary AS
SELECT 
    kg.tenant_id,
    o.name as organization_name,
    o.subscription_tier,
    COUNT(kg.id) as total_graphs,
    SUM(kg.node_count) as total_nodes,
    SUM(kg.edge_count) as total_edges,
    COUNT(CASE WHEN kg.is_public THEN 1 END) as public_graphs,
    AVG(kg.node_count) as avg_nodes_per_graph,
    MAX(kg.updated_at) as last_activity
FROM knowledge_graphs kg
JOIN organizations o ON kg.tenant_id = o.id
WHERE o.is_active = true
GROUP BY kg.tenant_id, o.name, o.subscription_tier;

-- Create unique index for efficient refresh
CREATE UNIQUE INDEX idx_tenant_usage_summary_tenant 
ON tenant_usage_summary(tenant_id);

-- Domain-specific analytics
CREATE MATERIALIZED VIEW domain_analytics AS
SELECT 
    domain,
    COUNT(*) as graph_count,
    AVG(node_count) as avg_nodes,
    AVG(edge_count) as avg_edges,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY node_count) as median_nodes,
    MAX(updated_at) as latest_update
FROM knowledge_graphs
WHERE node_count > 0
GROUP BY domain;

-- Refresh function for scheduled updates
CREATE OR REPLACE FUNCTION refresh_analytics_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY tenant_usage_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY domain_analytics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY knowledge_graph_stats;
END;
$$ LANGUAGE plpgsql;
