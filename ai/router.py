from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from .schemas import (
    PromptRequest,
    YamlRequest,
    ChatRequest,
    ChatResponse,
    FillRequest,
    NodeInfoRequest,
)
from pydantic import BaseModel
import subprocess
from pathlib import Path
from agents.generator import generate_yaml
from agents.explainer import explain_yaml
from agents.validator import validate_yaml, validate_usecase_prompt
from agents.component_designer import design_component
from agents.usecase_designer import design_usecase
from agents.filler import fill_code, store_details
from services.chat_agent import ChatAgent
from agents.coordinator import Coordinator
from .toolset import Toolset

router = APIRouter()
agent = ChatAgent()
tools = Toolset()
coordinator = Coordinator(tools)


class CompileRequest(BaseModel):
    file: str = "grafo.yaml"
    output: str | None = None


def _run_compile(file: str, output: str | None = None):
    cmd = [
        "cargo",
        "run",
        "--quiet",
        "--",
        "compile",
        file,
    ]
    if output:
        cmd.extend(["--output", output])
    proc = subprocess.Popen(
        cmd,
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    out, _ = proc.communicate()
    return {"ok": proc.returncode == 0, "logs": out.decode()}

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


@router.post("/node-info")
async def node_info_route(req: NodeInfoRequest):
    await run_in_threadpool(store_details, req.id, req.description, req.story)
    return {"ok": True}


@router.post("/refactor/yaml")
async def refactor_yaml_route(req: YamlRequest):
    text = await run_in_threadpool(tools.suggest_refactor, req.yaml, None)
    return {"text": text}


@router.post("/simulate/flow")
async def simulate_flow_route(req: YamlRequest):
    text = await run_in_threadpool(tools.simulate_flow, req.yaml, None)
    return {"text": text}


@router.post("/graph-rag")
async def graph_rag_route(req: PromptRequest):
    graph = await run_in_threadpool(tools.graph_rag, req.text)
    return {"graph": graph}


@router.post("/chat")
async def chat_route(req: ChatRequest) -> ChatResponse:
    reply = await run_in_threadpool(agent.chat, req.messages, req.model)
    return ChatResponse(message=reply)


@router.post("/ai-team")
async def ai_team_route(req: ChatRequest) -> ChatResponse:
    reply = await run_in_threadpool(coordinator.chat, req.messages, req.model)
    return ChatResponse(message=reply)


@router.post("/compile")
async def compile_route(req: CompileRequest):
    result = await run_in_threadpool(_run_compile, req.file, req.output)
    return result
