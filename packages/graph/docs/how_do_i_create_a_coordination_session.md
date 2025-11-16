# How do I create a coordination session?

## Summary
This guide shows how to start a multi-agent coordination session using the application's service layer.

## Prerequisites
- Python 3.11+
- The repository dependencies installed with `pip install -e .[dev]`
- Access to a running knowledge graph and active agents registered in the system

## Configuration
1. Copy `.env.example` to `.env` and adjust credentials for your graph database and LLM providers.
2. Ensure your agents are active and have the necessary permissions.

## Execution
1. Create an instance of `CreateCoordinationSessionUseCase` with concrete implementations of the required ports.
2. Build a `CreateCoordinationSessionRequestDTO` specifying tenant, user, knowledge graph id, strategy, and participating agents.
3. Call `use_case.execute(request)` to start the session. The first agent in the list acts as the orchestrator by default.

## Testing
Run `pytest -q` to execute the project's test suite and verify that your environment is correctly configured.
