"""Specialized experts for the coordinator AI team."""

import json
from ..toolset import Toolset

class BackendExpert:
    """Specialist in Rust backend and Ferrum architecture."""

    def __init__(self, tools: Toolset) -> None:
        self.tools = tools

    def respond(self, question: str, model: str | None = None) -> str:
        system = "You are a senior Rust backend engineer for Ferrum"
        # Example of using additional tools when the question mentions bottlenecks
        if "bottleneck" in question:
            try:
                result = self.tools.analyze_graph(question)
                analysis = json.dumps(result)
                question = f"{question}\nGraph analysis: {analysis}"
            except Exception:
                pass
        return self.tools.call_llm(question, system, model)

class FrontendExpert:
    """Specialist in React and TypeScript frontend."""

    def __init__(self, tools: Toolset) -> None:
        self.tools = tools

    def respond(self, question: str, model: str | None = None) -> str:
        system = "You are an expert React/TypeScript developer for Ferrum"
        return self.tools.call_llm(question, system, model)

class UXDesigner:
    """Expert in UX design and product usability."""

    def __init__(self, tools: Toolset) -> None:
        self.tools = tools

    def respond(self, question: str, model: str | None = None) -> str:
        system = "You are a UX designer focused on usability"
        return self.tools.call_llm(question, system, model)

__all__ = ["BackendExpert", "FrontendExpert", "UXDesigner"]
