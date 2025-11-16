from __future__ import annotations

import ast
from typing import Any, Dict


class ExpressionEvaluator:
    """Safely evaluate simple boolean expressions."""

    def __init__(self, variables: Dict[str, Any]):
        self.variables = variables

    def evaluate(self, expression: str) -> Any:
        tree = ast.parse(expression, mode="eval")
        return self._eval(tree.body)

    def _eval(self, node: ast.AST) -> Any:
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self._eval(v) for v in node.values)
            if isinstance(node.op, ast.Or):
                return any(self._eval(v) for v in node.values)
            raise ValueError(f"Unsupported boolean operator: {ast.dump(node.op)}")
        if isinstance(node, ast.Compare):
            left = self._eval(node.left)
            for op, comp in zip(node.ops, node.comparators):
                right = self._eval(comp)
                if isinstance(op, ast.Eq) and left != right:
                    return False
                if isinstance(op, ast.NotEq) and left == right:
                    return False
                if isinstance(op, ast.Gt) and not left > right:
                    return False
                if isinstance(op, ast.Lt) and not left < right:
                    return False
                if isinstance(op, ast.GtE) and not left >= right:
                    return False
                if isinstance(op, ast.LtE) and not left <= right:
                    return False
                left = right
            return True
        if isinstance(node, ast.Name):
            if node.id not in self.variables:
                raise ValueError(f"Undefined variable: {node.id}")
            return self.variables[node.id]
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not self._eval(node.operand)
        raise ValueError(f"Unsupported expression: {ast.dump(node)}")
