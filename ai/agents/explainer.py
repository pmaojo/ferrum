from ..services.llm_client import call_llm

def explain_yaml(yaml_text: str) -> str:
    system = "Explica el siguiente grafo.yaml"
    return call_llm(yaml_text, system, None)
