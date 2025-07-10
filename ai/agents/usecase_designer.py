from services.llm_client import call_llm


def design_usecase(prompt: str, model: str | None = None) -> str:
    """Generate a Ferrum usecase YAML from a natural language description."""
    system = "Convierte esta descripción en un usecase YAML para Ferrum"
    return call_llm(prompt, system, model)
