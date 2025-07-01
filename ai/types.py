from typing import Optional
from pydantic import BaseModel

class PromptRequest(BaseModel):
    text: str
    model: Optional[str] = None

class YamlRequest(BaseModel):
    yaml: str


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class FillRequest(BaseModel):
    task: str
    context: str
    model: Optional[str] = None
