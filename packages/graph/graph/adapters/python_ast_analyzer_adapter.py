"""AST-based Python code analyzer emitting ontology triples."""

from __future__ import annotations

import ast
from typing import List

from application.ports import CodeOntologyPort
from domain.entities import Triple


class PythonASTAnalyzerAdapter(CodeOntologyPort):
    """Extract ontology triples from Python source using ``ast``."""

    def extract_triples(
        self, *, code: str, repo_id: str, tenant_id: str
    ) -> List[Triple]:
        tree = ast.parse(code)
        triples: List[Triple] = []

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                triples.append(Triple(repo_id, "definesFunction", node.name, tenant_id))
            elif isinstance(node, ast.ClassDef):
                triples.append(Triple(repo_id, "definesClass", node.name, tenant_id))
                for body_node in node.body:
                    if isinstance(body_node, ast.FunctionDef):
                        triples.append(
                            Triple(node.name, "hasMethod", body_node.name, tenant_id)
                        )

        return triples
