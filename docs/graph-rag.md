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
