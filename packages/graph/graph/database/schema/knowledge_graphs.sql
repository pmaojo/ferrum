-- Knowledge Graphs Database Schema
-- This schema supports multi-tenancy, scientific domains, and efficient querying

-- Create knowledge_graphs table
CREATE TABLE knowledge_graphs (
    -- Primary identifier
    id VARCHAR(36) PRIMARY KEY,
    
    -- Basic information
    name VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(36) NOT NULL,
    
    -- Scientific domain (enum stored as string)
    domain VARCHAR(50) NOT NULL CHECK (
        domain IN (
            'biology', 'chemistry', 'physics', 'medicine', 
            'environmental_science', 'astronomy', 'general'
        )
    ),
    
    -- Ontology reference
    ontology_version_id VARCHAR(36) NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Graph statistics
    node_count INTEGER NOT NULL DEFAULT 0 CHECK (node_count >= 0),
    edge_count INTEGER NOT NULL DEFAULT 0 CHECK (edge_count >= 0),
    
    -- Visibility
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Constraints
    CONSTRAINT unique_name_per_tenant UNIQUE (name, tenant_id),
    CONSTRAINT valid_timestamps CHECK (updated_at >= created_at)
);

-- Create indexes for efficient querying
CREATE INDEX idx_knowledge_graphs_tenant_id ON knowledge_graphs(tenant_id);
CREATE INDEX idx_knowledge_graphs_domain ON knowledge_graphs(domain);
CREATE INDEX idx_knowledge_graphs_created_at ON knowledge_graphs(created_at);
CREATE INDEX idx_knowledge_graphs_updated_at ON knowledge_graphs(updated_at);
CREATE INDEX idx_knowledge_graphs_is_public ON knowledge_graphs(is_public);
CREATE INDEX idx_knowledge_graphs_node_count ON knowledge_graphs(node_count);
CREATE INDEX idx_knowledge_graphs_edge_count ON knowledge_graphs(edge_count);

-- Composite indexes for common query patterns
CREATE INDEX idx_knowledge_graphs_tenant_domain ON knowledge_graphs(tenant_id, domain);
CREATE INDEX idx_knowledge_graphs_tenant_public ON knowledge_graphs(tenant_id, is_public);
CREATE INDEX idx_knowledge_graphs_tenant_created ON knowledge_graphs(tenant_id, created_at DESC);

-- Full-text search index for name (PostgreSQL specific)
CREATE INDEX idx_knowledge_graphs_name_search ON knowledge_graphs USING gin(to_tsvector('english', name));

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_knowledge_graphs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_knowledge_graphs_updated_at
    BEFORE UPDATE ON knowledge_graphs
    FOR EACH ROW
    EXECUTE FUNCTION update_knowledge_graphs_updated_at();

-- Optional: Create a view for public knowledge graphs
CREATE VIEW public_knowledge_graphs AS
SELECT 
    id,
    name,
    tenant_id,
    domain,
    ontology_version_id,
    created_at,
    updated_at,
    node_count,
    edge_count
FROM knowledge_graphs
WHERE is_public = TRUE;

-- Optional: Create materialized view for statistics (refresh periodically)
CREATE MATERIALIZED VIEW knowledge_graph_stats AS
SELECT 
    tenant_id,
    domain,
    COUNT(*) as total_graphs,
    AVG(node_count) as avg_nodes,
    AVG(edge_count) as avg_edges,
    SUM(CASE WHEN is_public THEN 1 ELSE 0 END) as public_graphs,
    MAX(created_at) as latest_created
FROM knowledge_graphs
GROUP BY tenant_id, domain;

-- Create index on materialized view
CREATE INDEX idx_knowledge_graph_stats_tenant ON knowledge_graph_stats(tenant_id);

-- Add comments for documentation
COMMENT ON TABLE knowledge_graphs IS 'Stores knowledge graph metadata with multi-tenant support';
COMMENT ON COLUMN knowledge_graphs.id IS 'Unique identifier for the knowledge graph (UUID)';
COMMENT ON COLUMN knowledge_graphs.name IS 'Human-readable name of the knowledge graph';
COMMENT ON COLUMN knowledge_graphs.tenant_id IS 'Tenant identifier for multi-tenancy isolation';
COMMENT ON COLUMN knowledge_graphs.domain IS 'Scientific domain specialization';
COMMENT ON COLUMN knowledge_graphs.ontology_version_id IS 'Reference to the ontology version used';
COMMENT ON COLUMN knowledge_graphs.node_count IS 'Number of nodes in the knowledge graph';
COMMENT ON COLUMN knowledge_graphs.edge_count IS 'Number of edges in the knowledge graph';
COMMENT ON COLUMN knowledge_graphs.is_public IS 'Whether the knowledge graph is publicly accessible';

-- Sample data for testing (optional)
-- INSERT INTO knowledge_graphs (
--     id, name, tenant_id, domain, ontology_version_id, 
--     node_count, edge_count, is_public
-- ) VALUES 
-- (
--     'kg-001', 'Biology Research Graph', 'tenant-001', 'biology', 'onto-v1',
--     1000, 2500, false
-- ),
-- (
--     'kg-002', 'Chemistry Compounds', 'tenant-001', 'chemistry', 'onto-v2',
--     500, 1200, true
-- ),
-- (
--     'kg-003', 'Physics Concepts', 'tenant-002', 'physics', 'onto-v1',
--     750, 1800, false
-- );