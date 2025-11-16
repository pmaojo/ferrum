
-- Repository Ingestion Jobs Table

CREATE TABLE repository_ingestions (
    id VARCHAR(36) PRIMARY KEY,
    repo_id VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(36) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    result TEXT,
    result_path VARCHAR(255)
);

-- Document relationships and constraints
COMMENT ON COLUMN repository_ingestions.repo_id IS 'Identifier of the repository being ingested (references knowledge graph ID)';
COMMENT ON COLUMN repository_ingestions.tenant_id IS 'Tenant identifier for multi-tenant isolation';
COMMENT ON COLUMN repository_ingestions.status IS 'Current ingestion job status';
COMMENT ON COLUMN repository_ingestions.result IS 'Serialized ingestion result payload';
COMMENT ON COLUMN repository_ingestions.result_path IS 'Filesystem path to stored ingestion result artifact';

CREATE INDEX idx_repository_ingestions_tenant_id ON repository_ingestions(tenant_id);
CREATE INDEX idx_repository_ingestions_status ON repository_ingestions(status);
CREATE INDEX idx_repository_ingestions_created_at ON repository_ingestions(created_at);

CREATE OR REPLACE FUNCTION update_repository_ingestions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_repository_ingestions_updated_at
    BEFORE UPDATE ON repository_ingestions
    FOR EACH ROW
    EXECUTE FUNCTION update_repository_ingestions_updated_at();
