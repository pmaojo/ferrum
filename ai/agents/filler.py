import os
from neo4j import GraphDatabase
from services.llm_client import call_llm


def _get_graph_driver():
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER")
    password = os.environ.get("NEO4J_PASSWORD")
    if not all([uri, user, password]):
        return None
    return GraphDatabase.driver(uri, auth=(user, password))


def fetch_context(anchor: str) -> str:
    driver = _get_graph_driver()
    if driver is None:
        return ""
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (n {id: $id})-[:DEPENDS_ON]->(m) RETURN n.id as n, collect(m.id) as deps",
                id=anchor,
            )
            record = result.single()
            if record:
                deps = ", ".join(record["deps"]) if record["deps"] else ""
                return f"{record['n']} -> {deps}"
    finally:
        driver.close()
    return ""


def fill_code(task: str, anchor: str, model: str | None = None) -> str:
    context = fetch_context(anchor)
    system = "You complete Rust and TypeScript TODO markers using graph context."
    prompt = f"Fill code for {task} in {anchor}. Context: {context}"
    return call_llm(prompt, system, model)
