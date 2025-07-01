from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from .schemas import (
    PromptRequest,
    YamlRequest,
    ChatRequest,
    ChatResponse,
    FillRequest,
)
from agents.generator import generate_yaml
from agents.explainer import explain_yaml
from agents.validator import validate_yaml, validate_usecase_prompt
from agents.component_designer import design_component
from agents.usecase_designer import design_usecase
from agents.filler import fill_code
from services.chat_agent import ChatAgent
from agents.coordinator import Coordinator

router = APIRouter()
agent = ChatAgent()
coordinator = Coordinator()

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


@router.post("/generate/usecase")
@router.post("/generate-usecase")
async def generate_usecase_route(req: PromptRequest):
    yaml_code = await run_in_threadpool(design_usecase, req.text, req.model)
    return {"yaml": yaml_code}

@router.post("/explain/yaml")
async def explain_yaml_route(req: PromptRequest):
    text = await run_in_threadpool(explain_yaml, req.text)
    return {"explanation": text}

@router.post("/validate/yaml")
async def validate_yaml_route(req: YamlRequest):
    ok = await run_in_threadpool(validate_yaml, req.yaml)
    return {"valid": ok}


@router.post("/validate/usecase")
async def validate_usecase_route(req: PromptRequest):
    ok = await run_in_threadpool(validate_usecase_prompt, req.text, req.model)
    return {"valid": ok}


@router.post("/fill-todo")
async def fill_todo_route(req: FillRequest):
    code = await run_in_threadpool(fill_code, req.instructions, req.code, None)
    return {"code": code}


@router.post("/chat")
async def chat_route(req: ChatRequest) -> ChatResponse:
    reply = await run_in_threadpool(agent.chat, req.messages, req.model)
    return ChatResponse(message=reply)


@router.post("/ai-team")
async def ai_team_route(req: ChatRequest) -> ChatResponse:
    reply = await run_in_threadpool(coordinator.chat, req.messages, req.model)
    return ChatResponse(message=reply)
