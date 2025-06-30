import os
import yaml
from neo4j import GraphDatabase

from .usecase_designer import design_usecase


def validate_yaml(text: str) -> bool:
    try:
        yaml.safe_load(text)
        return True
    except yaml.YAMLError:
        return False


def _get_graph_driver():
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER")
    password = os.environ.get("NEO4J_PASSWORD")
    if not all([uri, user, password]):
        return None
    return GraphDatabase.driver(uri, auth=(user, password))


def validate_yaml_with_graph(text: str) -> bool:
    if not validate_yaml(text):
        return False

    driver = _get_graph_driver()
    if driver is None:
        return False

    data = yaml.safe_load(text)
    nodes = data.get("nodes", [])

    try:
        with driver.session() as session:
            for node in nodes:
                node_id = node.get("id")
                if node_id is None:
                    return False
                result = session.run("MATCH (n {id: $id}) RETURN n LIMIT 1", id=node_id)
                if result.single() is None:
                    return False

                for dep in node.get("depends_on", []):
                    dep_result = session.run(
                        "MATCH (a {id: $from})-[:DEPENDS_ON]->(b {id: $to}) RETURN b",
                        from=node_id,
                        to=dep,
                    )
                    if dep_result.single() is None:
                        return False
    finally:
        driver.close()

    return True


def validate_usecase_prompt(prompt: str, model: str | None = None) -> bool:
    yaml_code = design_usecase(prompt, model)
    return validate_yaml_with_graph(yaml_code)

