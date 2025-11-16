from services.generator import generate_yaml
from services.explainer import explain_yaml
from services.validator import validate_yaml, validate_usecase_prompt


def select(action: str):
    return {
        "generate": generate_yaml,
        "explain": explain_yaml,
        "validate": validate_yaml,
        "validate_usecase": validate_usecase_prompt,
    }.get(action)
