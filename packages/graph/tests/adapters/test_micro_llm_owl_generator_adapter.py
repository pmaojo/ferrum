import importlib.util

spec = importlib.util.spec_from_file_location(
    "micro_adapter", "adapters/micro_llm_owl_generator_adapter.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
MicroLLMOwlGeneratorAdapter = module.MicroLLMOwlGeneratorAdapter


class DummyLLM:
    def generate(self, *, prompt: str, tenant_id: str, stream: bool = False, tools=None, opts=None):
        return """Class: Person
ObjectProperty: knows
ClassAssertion: Person Alice"""


def test_generate_axioms_manchester():
    adapter = MicroLLMOwlGeneratorAdapter(DummyLLM())
    axioms = adapter.generate_axioms(text="Alice knows Bob", tenant_id="t1")
    prefixes = {
        "Class:",
        "ObjectProperty:",
        "DataProperty:",
        "Individual:",
        "ClassAssertion:",
        "ObjectPropertyAssertion:",
        "DataPropertyAssertion:",
        "SubClassOf:",
    }
    assert all(any(ax.startswith(p) for p in prefixes) for ax in axioms)


