from ..services.llm_client import call_llm


def design_component(prompt: str, model: str | None = None) -> str:
    """Generate a Ferrum component YAML from a natural language description."""
    system = "Convierte esta descripción en un componente YAML para Ferrum"
    return call_llm(prompt, system, model)
