from fastapi import APIRouter
from pydantic import BaseModel

from llm.openai import OpenAIBackend
from llm.local_llm import LocalLLMBackend
from llm.anthropic import AnthropicBackend

router = APIRouter()

backends = {
    "openai": OpenAIBackend(),
    "local": LocalLLMBackend(),
    "anthropic": AnthropicBackend(),
}

class PromptRequest(BaseModel):
    text: str
    backend: str = "openai"


@router.post("/generate-yaml")
async def generate_yaml(req: PromptRequest):
    backend = backends.get(req.backend)
    if not backend:
        return {"error": f"Unknown backend: {req.backend}"}
    yaml_code = backend.generate_yaml(req.text)
    return {"yaml": yaml_code}
