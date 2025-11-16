import pytest
from pathlib import Path
import tempfile
from unittest.mock import MagicMock

# Since the project structure is problematic, we might need to adjust the python path
# to import the necessary modules.
import sys
# We are in PermaGraph/tests, so we need to add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


from infrastructure.kthulu_doc_parser import KthuluDocParser
from domain.ontology.kthulu_ontology_loader import ComponentType
from domain.entities.triple import Triple

@pytest.fixture
def temp_req_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        req_dir = Path(tmpdir)

        # Format 1: id and code_links
        (req_dir / "req1.md").write_text(
            """---
id: REQ-001
code_links:
  - ../../backend/internal/modules/oauthsso/usecase/authorize.go
---
Some content
"""
        )

        # Format 2: module, usecase_name, source_file
        (req_dir / "oauthsso_token.md").write_text(
            """---
module: oauthsso
usecase_name: Token
source_file: ../../backend/internal/modules/oauthsso/usecase/token.go
---
Some content
"""
        )

        # A file that should be ignored
        (req_dir / "ignored.txt").write_text("This should be ignored")

        yield req_dir

def test_kthulu_doc_parser(temp_req_dir):
    # Mock the ontology loader
    mock_ontology_loader = MagicMock()
    mock_ontology_loader.NAMESPACE = "http://kthulu.io/ontology#"
    def create_component_iri(component_type, name, namespace):
        return f"{mock_ontology_loader.NAMESPACE}{namespace}.{component_type.value}.{name}"
    mock_ontology_loader.create_component_iri.side_effect = create_component_iri

    parser = KthuluDocParser(base_path=temp_req_dir, ontology_loader=mock_ontology_loader)
    triples = parser.parse_requirements()

    assert len(triples) == 2

    # The order is not guaranteed, so we check for both
    triples_by_subject = {t.subject: t for t in triples}

    # Check the triple from the first format
    triple1 = triples_by_subject["http://kthulu.io/ontology#Requirement.REQ-001"]
    assert triple1.predicate == "http://kthulu.io/ontology#satisfiesUseCase"
    assert triple1.object == "http://kthulu.io/ontology#oauthsso.UseCase.Authorize"
    assert "req1.md" in triple1.metadata["source_file"]

    # Check the triple from the second format
    triple2 = triples_by_subject["http://kthulu.io/ontology#Requirement.oauthsso_token"]
    assert triple2.predicate == "http://kthulu.io/ontology#satisfiesUseCase"
    assert triple2.object == "http://kthulu.io/ontology#oauthsso.UseCase.Token"
    assert "oauthsso_token.md" in triple2.metadata["source_file"]
