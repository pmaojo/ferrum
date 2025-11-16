import sys
from pathlib import Path
import yaml
from rdflib import Graph, Namespace, RDF, OWL


def convert(yaml_path: str, ttl_path: str, namespace_uri: str = "http://kronal.dev/optometry#") -> None:
    """Convert ontology YAML into OWL/RDF triples."""
    with open(yaml_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    g = Graph()
    onto = Namespace(namespace_uri)
    g.bind("onto", onto)
    g.bind("owl", OWL)

    # Collect all entity names
    ontology_cfg = data.get("ontology_config", {})
    entities = []
    official = ontology_cfg.get("official_entities", {})
    for group in official.values():
        if isinstance(group, list):
            entities.extend(group)
    entities.extend(ontology_cfg.get("custom_entities", []))

    for ent in entities:
        g.add((onto[ent], RDF.type, OWL.Class))

    # Relationships become object properties
    for rel in ontology_cfg.get("relationships", []):
        g.add((onto[rel], RDF.type, OWL.ObjectProperty))

    g.serialize(destination=ttl_path, format="turtle")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: yaml_to_rdf.py <input.yaml> <output.ttl> [namespace]", file=sys.stderr)
        sys.exit(1)
    yaml_path = sys.argv[1]
    ttl_path = sys.argv[2]
    namespace = sys.argv[3] if len(sys.argv) > 3 else "http://kronal.dev/optometry#"
    convert(yaml_path, ttl_path, namespace)
