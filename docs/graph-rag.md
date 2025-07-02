# GraphRAG

GraphRAG is a retrieval-augmented generation helper that queries a Neo4j graph
to provide relevant context for AI features. It uses the `id` field of nodes and
their `DEPENDS_ON` relations to build a small YAML snippet. This snippet is then
fed into the language model so it can reason about your architecture.

Ferrum ships two CLI commands that rely on this context:

```bash
ferrum fill-todos gen
```
Fill code blocks marked with `// ⛳️ AI_FILL[task] --context NODE_ID` using
GraphRAG to fetch dependencies for `NODE_ID`.

If the filler service returns an empty snippet, Ferrum will now ask you for a
short description or story about `NODE_ID`. The extra details are sent back to
`/fill-todo` and also stored in Neo4j so future calls have richer context.

```bash
ferrum ai-team "What affects the node `saveOrder`?"
```
Ask the coordinator agent a question. The experts automatically call GraphRAG
and include the resulting subgraph in their answer.

To enable GraphRAG, set the following environment variables so Ferrum can connect
to Neo4j:

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

The Docker compose file already exposes a Neo4j container. Make sure it is
running before using any GraphRAG-powered commands.

When you edit a node's description or story from the Studio context menu, the
changes are sent to the `/node-info` endpoint. The backend persists these
details in Neo4j so subsequent GraphRAG queries and tooltips reflect the latest
information.
