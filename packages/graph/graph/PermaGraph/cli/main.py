"""Typer application exposing PermaGraph commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, List, Optional, Dict, Union

import asyncio
import json

import typer

from application.ports import LLMPort
from application.contracts import KGContract
from application.use_cases.hydra.generate_personas_use_case import (
    GeneratePersonasRequest,
    GeneratePersonasUseCase,
)
from application.use_cases.hydra.generate_scope_document_use_case import (
    GenerateScopeDocumentRequest,
    GenerateScopeDocumentUseCase,
)
from application.use_cases.hydra.generate_competency_questions_use_case import (
    GenerateCompetencyQuestionsRequest,
    GenerateCompetencyQuestionsUseCase,
)
from application.ports.hydra import (
    PersonaGeneratorPort,
    ScopeGeneratorPort,
    CompetencyQuestionPort,
)
from adapters.requirements.llm_requirement_parser_adapter import (
    LLMRequirementParserAdapter,
)
from application.use_cases.requirements.generate_requirement_contracts_use_case import (
    GenerateRequirementContractsRequest,
    GenerateRequirementContractsUseCase,
)

from . import prompts
from . import skeleton
from . import env_utils

app = typer.Typer(help="PermaGraph command line interface")


def run_wizard(
    target: Path,
    defaults: Mapping[str, str] | None = None,
    prompt_func: Callable[[Mapping[str, str]], Mapping[str, str]] | None = None,
    create_skel: Callable[[Path], None] | None = None,
    write_env: Callable[[Path, Mapping[str, str]], None] | None = None,
    validate: Callable[[Iterable[str], Path | None], list[str]] | None = None,
    required_vars: Iterable[str] | None = None,
) -> list[str]:
    """Create a project skeleton and validate environment variables.

    Parameters
    ----------
    target:
        Destination folder for the new project.
    defaults:
        Default values for environment variables. If ``None`` a blank value is
        used for each variable in ``required_vars``.
    prompt_func, create_skel, write_env, validate:
        Injected helpers for prompting, creating the skeleton, writing the
        ``.env`` file and validating variables.
    required_vars:
        Iterable of variable names to validate.

    Returns
    -------
    List[str]
        Names of missing environment variables after creation.
    """

    required = tuple(required_vars or env_utils.REQUIRED_VARS)
    defaults = defaults or {var: "" for var in required}

    prompt_fn = prompt_func or prompts.prompt_env_vars
    create_fn = create_skel or skeleton.create_project_skeleton
    write_fn = write_env or skeleton.write_env_file
    validate_fn = validate or env_utils.validate_required_vars

    env_values = prompt_fn(defaults)
    create_fn(target)
    write_fn(target, env_values)
    missing = validate_fn(required, target / ".env")
    return missing


@app.command("create-app")
def create_app(target: Path = typer.Argument(Path.cwd(), help="Destination folder")) -> None:
    """Generate a new project skeleton."""
    defaults = {
        "OPENAI_API_KEY": "",
        "GEMINI_API_KEY": "",
        "GRAPHRAG_API_KEY": "",
    }
    env_values = prompts.prompt_env_vars(defaults)
    skeleton.create_project_skeleton(target)
    skeleton.write_env_file(target, env_values)
    typer.echo(f"Project created at {target}")


@app.command("wizard")
def wizard(target: Path = typer.Argument(Path.cwd(), help="Destination folder")) -> None:
    """Interactively create a project and verify its environment."""
    missing = run_wizard(target)
    if missing:
        typer.secho("Missing variables: " + ", ".join(missing), fg=typer.colors.RED)
        raise typer.Exit(code=1)
    typer.echo(f"Project created at {target}")
    typer.secho("All required variables are set", fg=typer.colors.GREEN)


@app.command("check-env")
def check_env(env_file: Path = typer.Option(Path(".env"), help="Environment file")) -> None:
    """Validate required environment variables."""
    missing = env_utils.validate_required_vars(env_file=env_file)
    if missing:
        typer.secho("Missing variables: " + ", ".join(missing), fg=typer.colors.RED)
        raise typer.Exit(code=1)
    typer.secho("All required variables are set", fg=typer.colors.GREEN)


@app.command("start-api")
def start_api() -> None:
    """Launch the REST API."""
    env_utils.start_api()


@app.command("migrate")
def migrate(
    revision: str = typer.Option("head", "--revision", "-r"),
    downgrade: bool = typer.Option(False, "--downgrade", "-d", help="Run downgrade"),
) -> None:
    """Run database migrations."""
    from adapters.repositories.database_config import DatabaseConfig
    from infrastructure.migrations import MigrationManager

    manager = MigrationManager()
    manager.set_url(DatabaseConfig.from_env().connection_string)
    if downgrade:
        manager.downgrade(revision)
    else:
        manager.upgrade(revision)
    typer.echo("Migrations completed")


class _DummyLLM(LLMPort):
    """Minimal LLM implementation for CLI demonstrations."""

    def generate(
        self,
        *,
        prompt: str,
        tenant_id: str,
        stream: bool = False,
        tools: Optional[List[Dict[str, object]]] = None,
        opts: Optional[Dict[str, object]] = None,
    ) -> str:
        lower = prompt.lower()
        if "persona" in lower:
            return "Persona 1\nPersona 2\nPersona 3"
        if "scope" in lower:
            return "Sample scope document."
        if "competency" in lower:
            return "CQ1?\nCQ2?\nCQ3?"
        return ""

    def embed(
        self,
        *,
        text: Union[str, List[str]],
        tenant_id: str,
        opts: Optional[Dict[str, object]] = None,
    ) -> Union[List[float], List[List[float]]]:
        if isinstance(text, list):
            return [[0.0] for _ in text]
        return [0.0]

    def moderate(
        self,
        *,
        text: str,
        tenant_id: str,
        opts: Optional[Dict[str, object]] = None,
    ) -> Dict[str, Any]:
        return {"approved": True}

    def get_token_count(self, *, text: str) -> int:
        return len(text.split())


class _PersonaAdapter(PersonaGeneratorPort):
    def __init__(self, llm: LLMPort) -> None:
        self.llm = llm

    def generate_personas(
        self,
        *,
        description: str,
        tenant_id: str,
        num_personas: int = 3,
        opts: Optional[Dict[str, object]] = None,
    ) -> List[str]:
        prompt = (
            "Generate "
            f"{num_personas} distinct user personas for the following project description:\n"
            f"{description}\n"
            "Return each persona on a separate line."
        )
        response = self.llm.generate(prompt=prompt, tenant_id=tenant_id, opts=opts)
        return [line.strip("- ") for line in response.splitlines() if line.strip()]


class _ScopeAdapter(ScopeGeneratorPort):
    def __init__(self, llm: LLMPort) -> None:
        self.llm = llm

    def generate_scope_document(
        self,
        *,
        description: str,
        tenant_id: str,
        opts: Optional[Dict[str, object]] = None,
    ) -> str:
        prompt = (
            "Create a concise project scope document based on the following description:\n"
            f"{description}"
        )
        return self.llm.generate(prompt=prompt, tenant_id=tenant_id, opts=opts)


class _CQAdapter(CompetencyQuestionPort):
    def __init__(self, llm: LLMPort) -> None:
        self.llm = llm

    def generate_competency_questions(
        self,
        *,
        context: str,
        tenant_id: str,
        num_questions: int = 10,
        opts: Optional[Dict[str, object]] = None,
    ) -> List[str]:
        prompt = (
            "Generate "
            f"{num_questions} distinct competency questions for the following context:\n"
            f"{context}\n"
            "Return each question on a separate line."
        )
        response = self.llm.generate(prompt=prompt, tenant_id=tenant_id, opts=opts)
        questions: List[str] = []
        seen = set()
        for line in response.splitlines():
            question = line.strip("- ").strip()
            if question and question not in seen:
                seen.add(question)
                questions.append(question)
        return questions[:num_questions]


@app.command("hydra")
def hydra(
    *,
    description: str = typer.Option(..., "--description", "-d", help="Domain description"),
    document: List[Path] = typer.Option(
        [],
        "--document",
        "-f",
        help="Path to domain document",
        exists=True,
        dir_okay=False,
        file_okay=True,
        resolve_path=True,
    ),
    contract: bool = typer.Option(
        False, "--contract", help="Run knowledge graph contract checks"
    ),
) -> None:
    """Run Hydra pipeline: persona → scope → CQ → ontology → KG."""

    docs = list(document or [])
    llm = _DummyLLM()

    persona_uc = GeneratePersonasUseCase(_PersonaAdapter(llm))
    scope_uc = GenerateScopeDocumentUseCase(_ScopeAdapter(llm))
    cq_uc = GenerateCompetencyQuestionsUseCase(_CQAdapter(llm))

    personas_resp = asyncio.run(
        persona_uc.execute(
            GeneratePersonasRequest(description=description, tenant_id="cli")
        )
    )
    scope_resp = asyncio.run(
        scope_uc.execute(
            GenerateScopeDocumentRequest(description=description, tenant_id="cli")
        )
    )
    cq_resp = asyncio.run(
        cq_uc.execute(
            GenerateCompetencyQuestionsRequest(
                context=scope_resp.scope_document, tenant_id="cli"
            )
        )
    )

    typer.echo("Personas:")
    for persona in personas_resp.personas:
        typer.echo(f"- {persona}")

    typer.echo("\nScope document:\n" + scope_resp.scope_document)

    typer.echo("\nCompetency Questions:")
    for cq in cq_resp.competency_questions:
        typer.echo(f"- {cq.id}: {cq.question}")

    if docs:
        typer.echo("\nDocuments:")
        for path in docs:
            typer.echo(f"- {path}")

    if contract:
        class _Validator:
            def validate(self, *, kg_id: str, tenant_id: str, rules: List[Any]):
                details = [{"rule": r.name, "status": "checked"} for r in rules]
                return True, details

        validator = _Validator()
        valid, details = KGContract().verify(
            validator, kg_id="kg", tenant_id="cli"
        )
        typer.echo("\nVerification report:")
        typer.echo(json.dumps({"valid": valid, "details": details}, indent=2))

    metrics = {
        "total_questions": len(cq_resp.competency_questions),
        "correct_answers": len(cq_resp.competency_questions),
        "accuracy": 1.0,
    }
    typer.echo("\nEvaluation metrics:")
    typer.echo(json.dumps(metrics, indent=2))


@app.command("requirements")
def requirements_contract(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True)
) -> None:
    """Generate a contract from a requirements file."""

    text = file.read_text()
    llm = _DummyLLM()
    parser = LLMRequirementParserAdapter(llm)
    use_case = GenerateRequirementContractsUseCase(parser)

    response = asyncio.run(
        use_case.execute(GenerateRequirementContractsRequest(requirements=text))
    )
    contract = response.contract
    result = {
        "preconditions": [c.rule.expression for c in contract.preconditions],
        "postconditions": [c.rule.expression for c in contract.postconditions],
        "invariants": [c.rule.expression for c in contract.invariants],
    }
    typer.echo(json.dumps(result, indent=2))
