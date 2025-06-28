from fastapi import FastAPI
from pydantic import BaseModel
import openai

app = FastAPI()

class PromptRequest(BaseModel):
    text: str
    model: str = "gpt-4"

@app.post("/generate-yaml")
async def generate_yaml(request: PromptRequest):
    response = openai.ChatCompletion.create(
        model=request.model,
        messages=[
            {"role": "system", "content": "Convert the following description into a Ferrum YAML specification..."},
            {"role": "user", "content": request.text}
        ]
    )
    yaml_content = response.choices[0].message.content
    return {"yaml": yaml_content}
