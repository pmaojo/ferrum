from fastapi import APIRouter
from types import PromptRequest, YamlRequest
from agents.generator import generate_yaml
from agents.explainer import explain_yaml
from agents.validator import validate_yaml

router = APIRouter()

@router.post("/generate/yaml")
@router.post("/generate-yaml")
async def generate_yaml_route(req: PromptRequest):
    yaml_code = generate_yaml(req.text)
    return {"yaml": yaml_code}

@router.post("/explain/yaml")
async def explain_yaml_route(req: PromptRequest):
    text = explain_yaml(req.text)
    return {"explanation": text}

@router.post("/validate/yaml")
async def validate_yaml_route(req: YamlRequest):
    ok = validate_yaml(req.yaml)
    return {"valid": ok}
