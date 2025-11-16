import tempfile
from pathlib import Path

from infrastructure.ferrus_doc_parser import FerrusDocParser


def test_ferrus_doc_parser_generates_triples():
    with tempfile.TemporaryDirectory() as tmpdir:
        req_dir = Path(tmpdir)
        (req_dir / "req1.md").write_text(
            """---
id: REQ-001
code_links:
  - src/modules/auth/usecases/login.rs
---
Some content
"""
        )

        parser = FerrusDocParser(base_path=req_dir)
        triples = parser.parse_requirements()

        assert len(triples) == 1
        t = triples[0]
        assert t.subject == "http://ferrus.io/ontology#Requirement.REQ-001"
        assert t.predicate == "http://ferrus.io/ontology#satisfiesUseCase"
        assert t.object == "http://ferrus.io/ontology#auth.UseCase.Login"
