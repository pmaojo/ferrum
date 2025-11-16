from __future__ import annotations

from typing import Any, Dict, List, Union

from domain.utils.expression_evaluator import ExpressionEvaluator


def resolve_template(template: str, data: Dict[str, Any]) -> str:
    result = template
    for key, value in data.items():
        if isinstance(value, (str, int, float, bool)):
            result = result.replace("{" + key + "}", str(value))
    return result


def resolve_docs(docs_spec: Union[List[str], Dict[str, Any], str], data: Dict[str, Any]) -> List[str]:
    if isinstance(docs_spec, list):
        return docs_spec
    if isinstance(docs_spec, dict):
        source = docs_spec.get("source", "")
        if source in data and isinstance(data[source], list):
            return data[source]
        if "default" in docs_spec:
            return docs_spec["default"]
        return []
    if isinstance(docs_spec, str) and docs_spec.startswith("{") and docs_spec.endswith("}"):
        key = docs_spec.strip("{}")
        value = data.get(key)
        return value if isinstance(value, list) else []
    raise ValueError(f"Invalid document specification type: {type(docs_spec)}")


def evaluate_condition(condition: Union[Dict[str, Any], str], data: Dict[str, Any]) -> bool:
    if isinstance(condition, str):
        try:
            return bool(ExpressionEvaluator(data).evaluate(condition))
        except Exception:
            return False
    op = condition.get("operator", "equals")
    left = resolve_operand(condition.get("left", ""), data)
    right = resolve_operand(condition.get("right", ""), data)
    if op == "equals":
        return left == right
    if op == "not_equals":
        return left != right
    if op == "contains":
        return right in left if isinstance(left, str) else False
    if op == "greater_than":
        return left > right if isinstance(left, (int, float)) and isinstance(right, (int, float)) else False
    if op == "less_than":
        return left < right if isinstance(left, (int, float)) and isinstance(right, (int, float)) else False
    if op == "exists":
        return left is not None
    raise ValueError(f"Unsupported condition operator: {op}")


def resolve_operand(operand: Any, data: Dict[str, Any]) -> Any:
    if isinstance(operand, dict) and "field" in operand:
        value = data
        for key in operand["field"].split("."):
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    return operand
