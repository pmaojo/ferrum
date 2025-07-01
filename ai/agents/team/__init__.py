from services.llm_client import call_llm

class BackendExpert:
    """Specialist in Rust backend and Ferrum architecture."""
    def respond(self, question: str, model: str | None = None) -> str:
        system = "You are a senior Rust backend engineer for Ferrum"
        return call_llm(question, system, model)

class FrontendExpert:
    """Specialist in React and TypeScript frontend."""
    def respond(self, question: str, model: str | None = None) -> str:
        system = "You are an expert React/TypeScript developer for Ferrum"
        return call_llm(question, system, model)

class UXDesigner:
    """Expert in UX design and product usability."""
    def respond(self, question: str, model: str | None = None) -> str:
        system = "You are a UX designer focused on usability"
        return call_llm(question, system, model)

__all__ = ["BackendExpert", "FrontendExpert", "UXDesigner"]
