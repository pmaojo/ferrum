# Real-time Event Contract

SCG uses WebSocket messages to notify clients of background activity. Each
message follows a common envelope:

```json
{
  "type": "<event type>",
  "projectId": "<project identifier>",
  "data": { ... },
  "timestamp": "ISO-8601 timestamp"
}
```

## Event Types

### `cli.progress`

Emitted as a CLI command produces output. The `data` field contains the raw
stdout/stderr chunk.

### `cli.done`

Sent when a CLI command finishes. `data` includes `{ exitCode, stdout, stderr }`.

### `graph.updated`

Broadcast when the architecture graph changes. `data` carries the update
payload.

### `graph_events`

Batch of fine-grained graph mutations. The message groups individual events
under `events`:

```json
{
  "type": "graph_events",
  "events": [
    {
      "event_type": "NODE_ADDED",
      "data": { "id": "node-1", "label": "Example" },
      "timestamp": "2024-01-01T00:00:00Z",
      "kg_id": "project-123"
    }
  ]
}
```

Supported `event_type` values include `NODE_ADDED` and `EDGE_ADDED`. Clients
should aggregate these into the previous `graph.updated` payload shape if they
need the summarized view of graph changes.

### `permagraph.synced`

Indicates that a PermaGraph synchronization cycle has completed. `data`
contains additional details about the sync result.

Clients should automatically reconnect when the connection drops and queue any
outgoing messages until the socket is re-established.
