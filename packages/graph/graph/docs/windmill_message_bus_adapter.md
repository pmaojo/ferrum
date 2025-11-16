# Windmill Message Bus Adapter

The `WindmillMessageBusAdapter` provides a minimal integration with
[Windmill](https://www.windmill.dev/)'s HTTP message bus.  It exposes a single
method, `publish`, which forwards events to the `/publish` endpoint.

Windmill's HTTP API does **not** offer a server-side subscription capability, so
`subscribe` is intentionally unsupported and will raise a
`SubscriptionError`. If your application needs to consume events from
Windmill, use the `WindmillMCPAdapter` instead. That adapter communicates with
Windmill's Model Context Protocol (MCP) using Server-Sent Events (SSE) to
receive messages in real time.

```python
from adapters.windmill_mcp_adapter import WindmillMCPAdapter
```

The MCP adapter enables both publishing and subscribing to topics, allowing
full duplex messaging with a Windmill deployment.
