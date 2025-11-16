import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

def _load_adapter(name: str):
    path = ROOT / "adapters" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    return getattr(module, ''.join(part.capitalize() for part in name.split('_')))

SimpleSparqlTranslatorAdapter = _load_adapter("simple_sparql_translator_adapter")
SimpleShaclTranslatorAdapter = _load_adapter("simple_shacl_translator_adapter")


def test_simple_sparql_translator_generates_query():
    translator = SimpleSparqlTranslatorAdapter()
    query, explanation = translator.translate(
        natural_language="Find Alice", kg_id="kg", tenant_id="t"
    )
    assert "SELECT" in query
    assert "alice" in query.lower()
    assert explanation


def test_simple_shacl_translator_generates_shape():
    translator = SimpleShaclTranslatorAdapter()
    shape, explanation = translator.translate(
        natural_language="Person must have email", kg_id="kg", tenant_id="t"
    )
    assert "NodeShape" in shape
    assert "email" in shape
    assert explanation
