# Full Demo

Example showcasing multiple Ferrum plugins working together.
It enables password auth, GraphQL schema generation and a cron job.

```bash
# install ferrum locally
cargo install --path ../..

# add required plugins and compile
ferrum add auth-password
ferrum add graphql
ferrum add cron
ferrum compile gen/app.yaml

# run the app
ferrum dev
```

After compilation you can sync the graph to Neo4j and use GraphRAG features:

```bash
# optional: sync to Neo4j for GraphRAG
ferrum sync gen/app.yaml bolt://localhost:7687 neo4j password

# ask the AI team a question about your architecture
ferrum ai-team "What does example_job depend on?"
```

See [docs/graph-rag.md](../../docs/graph-rag.md) for details on GraphRAG commands.
