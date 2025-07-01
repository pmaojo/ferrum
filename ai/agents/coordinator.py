"""High level coordinator agent delegating tasks to specialized agents."""
from typing import List, Dict

from .generator import generate_yaml
from .validator import validate_yaml
from .filler import fill_code
from .team import BackendExpert, FrontendExpert, UXDesigner
from ..toolset import Toolset


class Coordinator:
    def __init__(self, tools: Toolset | None = None) -> None:
        self.tools = tools or Toolset()
        self.backend = BackendExpert(self.tools)
        self.frontend = FrontendExpert(self.tools)
        self.ux = UXDesigner(self.tools)

    def chat(self, messages: List[Dict[str, str]], model: str | None = None) -> str:
        """Respond to a user message by delegating to specialized agents."""
        if not messages:
            return ""
        text = messages[-1].get("content", "")

        if text.startswith("generate "):
            prompt = text[len("generate "):]
            return generate_yaml(prompt, model)
        if text.startswith("validate "):
            yaml_text = text[len("validate "):]
            ok = validate_yaml(yaml_text)
            return "valid" if ok else "invalid"
        if text.startswith("fill "):
            parts = text.split(maxsplit=2)
            if len(parts) == 3:
                return fill_code(parts[1], parts[2], model)

        back = self.backend.respond(text, model)
        front = self.frontend.respond(text, model)
        ux = self.ux.respond(text, model)
        return "\n\n".join([
            "Backend Expert:\n" + back,
            "Frontend Expert:\n" + front,
            "UX Designer:\n" + ux,
        ])

