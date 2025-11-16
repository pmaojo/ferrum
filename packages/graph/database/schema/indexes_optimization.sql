
-- Advanced Database Optimizations
-- Additional indexes and performance improvements

-- Composite index for tenant-filtered queries with pagination
CREATE INDEX CONCURRENTLY idx_knowledge_graphs_tenant_created_pagination 
ON knowledge_graphs(tenant_id, created_at DESC, id);

-- Partial index for active entities only
CREATE INDEX CONCURRENTLY idx_knowledge_graphs_active_public 
ON knowledge_graphs(tenant_id, domain) 
WHERE is_public = true;

-- Full-text search optimization
CREATE INDEX CONCURRENTLY idx_knowledge_graphs_name_gin 
ON knowledge_graphs 
USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));

-- Query performance for analytics
CREATE INDEX CONCURRENTLY idx_knowledge_graphs_stats 
ON knowledge_graphs(tenant_id, domain, node_count, edge_count) 
WHERE node_count > 0;

-- Subscription queries optimization
CREATE INDEX CONCURRENTLY idx_subscriptions_active_billing 
ON subscriptions(organization_id, status, expires_at) 
WHERE status = 'active';

-- User activity optimization
CREATE INDEX CONCURRENTLY idx_users_active_org 
ON users(organization_id, is_active, last_login DESC) 
WHERE is_active = true;
