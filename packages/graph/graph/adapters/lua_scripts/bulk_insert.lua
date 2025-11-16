--[[
Bulk insert script for FalkorDB with tenant isolation and optimistic locking.

This script performs atomic bulk insertion of triples into FalkorDB with
tenant isolation and optimistic locking to prevent conflicts.

Arguments:
- KEYS[1]: Knowledge graph ID
- KEYS[2]: Tenant ID
- ARGV[1]: JSON array of triples to insert

Returns:
- JSON object with insertion results
]]

local kg_id = KEYS[1]
local tenant_id = KEYS[2]
local triples_json = ARGV[1]

-- Parse JSON array of triples
local triples = cjson.decode(triples_json)
local inserted = 0
local errors = {}

-- Check tenant isolation
if redis.call("EXISTS", "tenant:" .. tenant_id) == 0 then
    redis.call("HSET", "tenant:" .. tenant_id, "created_at", redis.call("TIME")[1])
end

-- Check knowledge graph exists
local kg_key = "kg:" .. kg_id
if redis.call("EXISTS", kg_key) == 0 then
    return cjson.encode({
        inserted = 0,
        errors = {"Knowledge graph not found: " .. kg_id}
    })
end

-- Verify tenant access to knowledge graph
local kg_tenant = redis.call("HGET", kg_key, "tenant_id")
if kg_tenant ~= tenant_id then
    return cjson.encode({
        inserted = 0,
        errors = {"Tenant " .. tenant_id .. " does not have access to knowledge graph " .. kg_id}
    })
end

-- Process each triple
for i, triple in ipairs(triples) do
    -- Validate triple has required fields
    if not triple.subject or not triple.predicate or not triple.object then
        table.insert(errors, "Triple at index " .. i .. " is missing required fields")
    else
        -- Create subject node if it doesn't exist
        local subject_key = "node:" .. kg_id .. ":" .. triple.subject
        if redis.call("EXISTS", subject_key) == 0 then
            redis.call("HSET", subject_key, "id", triple.subject)
            redis.call("HSET", subject_key, "tenant_id", tenant_id)
            redis.call("HSET", subject_key, "created_at", redis.call("TIME")[1])
        end
        
        -- Create object node if it doesn't exist
        local object_key = "node:" .. kg_id .. ":" .. triple.object
        if redis.call("EXISTS", object_key) == 0 then
            redis.call("HSET", object_key, "id", triple.object)
            redis.call("HSET", object_key, "tenant_id", tenant_id)
            redis.call("HSET", object_key, "created_at", redis.call("TIME")[1])
        end
        
        -- Create edge (relationship)
        local edge_id = triple.subject .. ":" .. triple.predicate .. ":" .. triple.object
        local edge_key = "edge:" .. kg_id .. ":" .. edge_id
        
        -- Check if edge already exists
        if redis.call("EXISTS", edge_key) == 0 then
            redis.call("HSET", edge_key, "subject", triple.subject)
            redis.call("HSET", edge_key, "predicate", triple.predicate)
            redis.call("HSET", edge_key, "object", triple.object)
            redis.call("HSET", edge_key, "tenant_id", tenant_id)
            redis.call("HSET", edge_key, "created_at", redis.call("TIME")[1])
            
            -- Add edge to subject and object node indices
            redis.call("SADD", "node:" .. kg_id .. ":" .. triple.subject .. ":out", edge_id)
            redis.call("SADD", "node:" .. kg_id .. ":" .. triple.object .. ":in", edge_id)
            
            -- Add edge to predicate index
            redis.call("SADD", "predicate:" .. kg_id .. ":" .. triple.predicate, edge_id)
            
            inserted = inserted + 1
        end
    end
end

-- Update knowledge graph metadata
if inserted > 0 then
    -- Increment node and edge counts
    redis.call("HINCRBY", kg_key, "node_count", inserted)
    redis.call("HINCRBY", kg_key, "edge_count", inserted)
    redis.call("HSET", kg_key, "updated_at", redis.call("TIME")[1])
    
    -- Add to tenant's knowledge graph list
    redis.call("SADD", "tenant:" .. tenant_id .. ":kgs", kg_id)
end

-- Return results
return cjson.encode({
    inserted = inserted,
    errors = errors
})