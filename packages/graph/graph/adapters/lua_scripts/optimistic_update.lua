--[[
Optimistic update of knowledge graph metadata.

KEA: KEYS[1] = knowledge graph key
ARGV[1] = nodes added
ARGV[2] = edges added
ARGV[3] = updated timestamp
]]

if redis.call("EXISTS", KEYS[1]) == 0 then
    return cjson.encode({ success = false, error = "kg not found" })
end

redis.call("HINCRBY", KEYS[1], "node_count", tonumber(ARGV[1]))
redis.call("HINCRBY", KEYS[1], "edge_count", tonumber(ARGV[2]))
redis.call("HSET", KEYS[1], "updated_at", ARGV[3])

return cjson.encode({ success = true })

