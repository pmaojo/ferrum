from ..agents import generator, explainer, validator


def select(action: str):
    return {
        "generate": generator.generate_yaml,
        "explain": explainer.explain_yaml,
        "validate": validator.validate_yaml,
        "validate_usecase": validator.validate_usecase_prompt,
    }.get(action)
