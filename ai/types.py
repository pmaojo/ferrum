from typing import Optional
from pydantic import BaseModel

class PromptRequest(BaseModel):
    text: str
    model: Optional[str] = None

class YamlRequest(BaseModel):
    yaml: str
