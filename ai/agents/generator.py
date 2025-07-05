from ..services.llm_client import call_llm

def generate_yaml(prompt: str, model: str | None = None) -> str:
    system = "Convierte esta descripción en un grafo.yaml"
    return call_llm(prompt, system, model)
