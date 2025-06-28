from pydantic import BaseModel

class PromptRequest(BaseModel):
    text: str

class YamlRequest(BaseModel):
    yaml: str
