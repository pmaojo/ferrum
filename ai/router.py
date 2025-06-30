from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from .types import PromptRequest, YamlRequest, ChatRequest, ChatResponse
from agents.generator import generate_yaml
from agents.explainer import explain_yaml
from agents.validator import validate_yaml
from agents.component_designer import design_component
from services.chat_agent import ChatAgent

router = APIRouter()
agent = ChatAgent()

@router.post("/generate/yaml")
@router.post("/generate-yaml")
async def generate_yaml_route(req: PromptRequest):
    yaml_code = await run_in_threadpool(generate_yaml, req.text, req.model)
    return {"yaml": yaml_code}


@router.post("/generate/component")
@router.post("/generate-component")
async def generate_component_route(req: PromptRequest):
    yaml_code = await run_in_threadpool(design_component, req.text, req.model)
    return {"yaml": yaml_code}

@router.post("/explain/yaml")
async def explain_yaml_route(req: PromptRequest):
    text = await run_in_threadpool(explain_yaml, req.text)
    return {"explanation": text}

@router.post("/validate/yaml")
async def validate_yaml_route(req: YamlRequest):
    ok = await run_in_threadpool(validate_yaml, req.yaml)
    return {"valid": ok}


@router.post("/chat")
async def chat_route(req: ChatRequest) -> ChatResponse:
    reply = await run_in_threadpool(agent.chat, req.message, None)
    return ChatResponse(reply=reply)
