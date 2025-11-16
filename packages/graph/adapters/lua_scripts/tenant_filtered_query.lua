--[[
Tenant-filtered query script for FalkorDB with performance optimization.

This script executes Cypher queries with automatic tenant isolation,
query optimization, and performance monitoring.

Arguments:
- KEYS[1]: Knowledge graph ID
- KEYS[2]: Tenant ID
- ARGV[1]: Cypher query string
- ARGV[2]: JSON object with query parameters
- ARGV[3]: Timeout in milliseconds

Returns:
- JSON object with query results and performance metrics
]]

local kg_id = KEYS[1]
local tenant_id = KEYS[2]
local cypher_query = ARGV[1]
local params_json = ARGV[2]
local timeout_ms = tonumber(ARGV[3]) or 30000

-- Parse query parameters
local params = cjson.decode(params_json)
local start_time = redis.call("TIME")

-- Check tenant isolation
if redis.call("EXISTS", "tenant:" .. tenant_id) == 0 then
    return cjson.encode({
        results = {},
        error = "Tenant not found: " .. tenant_id,
        execution_time_ms = 0,
        metrics = {}
    })
end

-- Check knowledge graph exists and tenant has access
local kg_key = "kg:" .. kg_id
if redis.call("EXISTS", kg_key) == 0 then
    return cjson.encode({
        results = {},
        error = "Knowledge graph not found: " .. kg_id,
        execution_time_ms = 0,
        metrics = {}
    })
end

local kg_tenant = redis.call("HGET", kg_key, "tenant_id")
if kg_tenant ~= tenant_id then
    return cjson.encode({
        results = {},
        error = "Tenant " .. tenant_id .. " does not have access to knowledge graph " .. kg_id,
        execution_time_ms = 0,
        metrics = {}
    })
end

-- Initialize metrics
local metrics = {
    nodes_scanned = 0,
    edges_scanned = 0,
    index_hits = 0,
    cache_hits = 0
}

-- Query optimization: Check for common patterns and use indices
local results = {}
local query_lower = string.lower(cypher_query)

-- Pattern 1: Simple node lookup by ID
local node_id_pattern = "match%s*%(%s*n%s*{%s*id%s*:%s*['\"]([^'\"]+)['\"]%s*}%s*%)"
local node_id = string.match(query_lower, node_id_pattern)

if node_id then
    -- Optimized node lookup using direct key access
    local node_key = "node:" .. kg_id .. ":" .. node_id
    if redis.call("EXISTS", node_key) == 1 then
        local node_data = redis.call("HGETALL", node_key)
        local node_obj = {}
        for i = 1, #node_data, 2 do
            node_obj[node_data[i]] = node_data[i + 1]
        end
        table.insert(results, {n = node_obj})
        metrics.index_hits = metrics.index_hits + 1
    end
    metrics.nodes_scanned = 1
    
-- Pattern 2: Relationship traversal by predicate
elseif string.match(query_lower, "%--%[%s*:%s*([^%]]+)%s*%]%-%-") then
    local predicate = string.match(query_lower, "%--%[%s*:%s*([^%]]+)%s*%]%--")
    
    -- Use predicate index for efficient traversal
    local predicate_key = "predicate:" .. kg_id .. ":" .. predicate
    local edge_ids = redis.call("SMEMBERS", predicate_key)
    
    for _, edge_id in ipairs(edge_ids) do
        local edge_key = "edge:" .. kg_id .. ":" .. edge_id
        local edge_data = redis.call("HGETALL", edge_key)
        
        if #edge_data > 0 then
            local edge_obj = {}
            for i = 1, #edge_data, 2 do
                edge_obj[edge_data[i]] = edge_data[i + 1]
            end
            table.insert(results, {r = edge_obj})
            metrics.edges_scanned = metrics.edges_scanned + 1
        end
    end
    metrics.index_hits = metrics.index_hits + 1
    
-- Pattern 3: Full graph traversal (expensive - apply limits)
elseif string.match(query_lower, "match%s*%(%s*n%s*%)") then
    -- Get all nodes for this knowledge graph and tenant
    local node_pattern = "node:" .. kg_id .. ":*"
    local node_keys = redis.call("KEYS", node_pattern)
    
    -- Apply limit to prevent expensive operations
    local limit = params.limit or 100
    local count = 0
    
    for _, node_key in ipairs(node_keys) do
        if count >= limit then
            break
        end
        
        local node_tenant = redis.call("HGET", node_key, "tenant_id")
        if node_tenant == tenant_id then
            local node_data = redis.call("HGETALL", node_key)
            local node_obj = {}
            for i = 1, #node_data, 2 do
                node_obj[node_data[i]] = node_data[i + 1]
            end
            table.insert(results, {n = node_obj})
            count = count + 1
        end
        metrics.nodes_scanned = metrics.nodes_scanned + 1
    end
    
-- Pattern 4: Complex queries - delegate to graph engine
else
    -- Delegate to the underlying graph engine using GRAPH.QUERY
    local response = redis.call("GRAPH.QUERY", kg_id, cypher_query, "--compact", "timeout", timeout_ms)
    local header = response[1] or {}
    local rows = response[2] or {}
    results = {}

    for i, row in ipairs(rows) do
        local row_obj = {}
        for j, value in ipairs(row) do
            local col = header[j]
            row_obj[col] = value
        end
        table.insert(results, row_obj)
    end

    metrics.engine_stats = response[#response]
end

-- Calculate execution time
local end_time = redis.call("TIME")
local execution_time_ms = (end_time[1] - start_time[1]) * 1000 + (end_time[2] - start_time[2]) / 1000

-- Update query statistics
local stats_key = "stats:" .. kg_id .. ":" .. tenant_id
redis.call("HINCRBY", stats_key, "query_count", 1)
redis.call("HINCRBY", stats_key, "total_execution_time_ms", math.floor(execution_time_ms))
redis.call("HSET", stats_key, "last_query_time", end_time[1])

-- Record performance metrics
if execution_time_ms > 1000 then
    redis.call("HINCRBY", stats_key, "slow_query_count", 1)
end

-- Return results with performance metrics
return cjson.encode({
    results = results,
    execution_time_ms = execution_time_ms,
    metrics = metrics,
    result_count = #results
})