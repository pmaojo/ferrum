from __future__ import annotations

from typing import Any, Dict, Optional

from application.ports import GraphRetrieverPort
from domain.entities import GraphStreamEventType

from .utils import evaluate_condition, resolve_docs, resolve_template


class StepExecutor:
    """Execute workflow steps and fallbacks."""

    def __init__(self, retriever: GraphRetrieverPort) -> None:
        self._retriever = retriever

    def execute_step(
        self,
        step: Dict[str, Any],
        input_data: Dict[str, Any],
        workflow_id: str,
        tenant_id: str,
    ) -> Dict[str, Any]:
        step_type = step["type"]
        if step_type == "graphrag_query":
            question = resolve_template(step["question"], input_data)
            kg_id = step.get("kg_id", "default")
            result = self._retriever.run(question=question, kg_id=kg_id, tenant_id=tenant_id, opts=step.get("opts", {}))
            return {"result": result, "question": question, "kg_id": kg_id}
        if step_type == "graphrag_index":
            docs = resolve_docs(step["docs"], input_data)
            kg_id = step.get("kg_id", "default")
            triples = self._retriever.index(docs=docs, kg_id=kg_id, tenant_id=tenant_id)
            return {"triples": [t._asdict() for t in triples], "count": len(triples), "kg_id": kg_id}
        if step_type == "custom_function":
            func_name = step["function"]
            if func_name not in step:
                raise ValueError(f"Custom function not found: {func_name}")
            function = step[func_name]
            return function(input_data)
        if step_type == "condition":
            condition = step["condition"]
            then_result = self.execute_step(step=step["then"], input_data=input_data, workflow_id=workflow_id, tenant_id=tenant_id)
            else_result = None
            if "else" in step:
                else_result = self.execute_step(step=step["else"], input_data=input_data, workflow_id=workflow_id, tenant_id=tenant_id)
            return then_result if evaluate_condition(condition, input_data) else (else_result if else_result is not None else input_data)
        raise ValueError(f"Unsupported step type: {step_type}")

    def execute_fallback(
        self,
        fallback: Dict[str, Any],
        input_data: Dict[str, Any],
        error: str,
        workflow_id: str,
        tenant_id: str,
    ) -> Dict[str, Any]:
        f_type = fallback.get("type", "default")
        if f_type == "retry":
            max_retries = fallback.get("max_retries", 3)
            for _ in range(max_retries):
                try:
                    modified_step = fallback.get("modified_step", {})
                    return self.execute_step(modified_step, input_data, workflow_id, tenant_id)
                except Exception:
                    continue
            raise ValueError(f"All {max_retries} retry attempts failed")
        if f_type == "alternative":
            alternative_step = fallback.get("step", {})
            return self.execute_step(alternative_step, input_data, workflow_id, tenant_id)
        if f_type == "default":
            return fallback.get("value", {"error": error, "fallback": "default"})
        return self.execute_step(fallback, input_data, workflow_id, tenant_id)
