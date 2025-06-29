import yaml


def validate_yaml(text: str) -> bool:
    try:
        yaml.safe_load(text)
        return True
    except yaml.YAMLError:
        return False
