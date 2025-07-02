from typing import Optional, List
from pydantic import BaseModel

class PromptRequest(BaseModel):
    text: str
    model: Optional[str] = "gpt-4"

class YamlRequest(BaseModel):
    yaml: str

class ChatRequest(BaseModel):
    messages: List[dict]
    model: Optional[str] = "gpt-4"

class ChatResponse(BaseModel):
    message: str

class FillRequest(BaseModel):
    code: str
    instructions: str


class NodeInfoRequest(BaseModel):
    id: str
    description: Optional[str] = None
    story: Optional[str] = None
