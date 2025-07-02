"""Helpers for filling TODO markers using GraphRAG context."""

import os
from neo4j import GraphDatabase
from services.llm_client import call_llm


def _get_graph_driver():
    """Return a Neo4j driver if graph configuration is present."""

    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER")
    password = os.environ.get("NEO4J_PASSWORD")
    if not all([uri, user, password]):
        return None
    return GraphDatabase.driver(uri, auth=(user, password))


def fetch_context(anchor: str) -> str:
    """Return a YAML snippet with node info and dependencies."""

    driver = _get_graph_driver()
    if driver is None:
        return ""
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (n {id: $id})
                OPTIONAL MATCH (n)-[:DEPENDS_ON]->(m)
                WITH n, collect(DISTINCT m.id) AS calls
                OPTIONAL MATCH (p)-[:DEPENDS_ON]->(n)
                RETURN n.id AS n, n.description AS description, n.story AS story,
                       calls, collect(DISTINCT p.id) AS used_by
                """,
                id=anchor,
            )
            record = result.single()
            if record:
                lines = [f"- name: {record['n']}"]
                if record.get("description"):
                    lines.append(f"  description: {record['description']}")
                if record.get("story"):
                    lines.append(f"  story: {record['story']}")
                calls = [c for c in record["calls"] if c]
                used_by = [u for u in record["used_by"] if u]
                if calls:
                    lines.append(f"  calls: [{', '.join(calls)}]")
                if used_by:
                    lines.append(f"  used_by: [{', '.join(used_by)}]")
                return "\n".join(lines)
    finally:
        driver.close()
    return ""


def fill_code(task: str, anchor: str, model: str | None = None) -> str:
    """Return code for a TODO marker using GraphRAG context."""

    context = fetch_context(anchor)
    system = "You complete Rust and TypeScript TODO markers using graph context."
    prompt = f"Fill code for {task} in {anchor}. Context: {context}"
    return call_llm(prompt, system, model)


def store_details(node_id: str, description: str | None = None, story: str | None = None) -> None:
    """Persist extra node details in Neo4j."""

    driver = _get_graph_driver()
    if driver is None:
        return
    try:
        with driver.session() as session:
            session.run(
                "MERGE (n {id: $id}) SET n.description = coalesce($desc, n.description), n.story = coalesce($story, n.story)",
                id=node_id,
                desc=description,
                story=story,
            )
    finally:
        driver.close()
