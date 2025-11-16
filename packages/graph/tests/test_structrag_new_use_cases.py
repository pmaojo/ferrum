import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest


def _load(module_path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, Path(module_path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    # Inject minimal ports module to satisfy imports without loading full package
    import types, sys
    if "application.ports" not in sys.modules:
        ports_stub = types.ModuleType("application.ports")
        sys.modules["application.ports"] = ports_stub
    exec("class StructRAGRouterPort: ...", sys.modules["application.ports"].__dict__)
    exec("class StructRAGDecompositionPort: ...", sys.modules["application.ports"].__dict__)
    exec("class StructRAGStructurizerPort: ...", sys.modules["application.ports"].__dict__)
    exec("class StructRAGTrainingPipelinePort: ...", sys.modules["application.ports"].__dict__)
    exec("class StructRAGMultiHopReasoningPort: ...", sys.modules["application.ports"].__dict__)
    exec("class StructRAGStatisticalAnalysisPort: ...", sys.modules["application.ports"].__dict__)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return getattr(module, name)


StructRAGRouterUseCase = _load(
    "application/use_cases/structrag/router_use_case.py", "StructRAGRouterUseCase"
)
StructRAGDecompositionUseCase = _load(
    "application/use_cases/structrag/decomposition_use_case.py",
    "StructRAGDecompositionUseCase",
)
StructRAGStructurizerUseCase = _load(
    "application/use_cases/structrag/structurizer_use_case.py",
    "StructRAGStructurizerUseCase",
)
StructRAGTrainingPipelineUseCase = _load(
    "application/use_cases/structrag/training_pipeline_use_case.py",
    "StructRAGTrainingPipelineUseCase",
)
StructRAGMultiHopReasoningUseCase = _load(
    "application/use_cases/structrag/multi_hop_reasoning_use_case.py",
    "StructRAGMultiHopReasoningUseCase",
)
StructRAGStatisticalAnalysisUseCase = _load(
    "application/use_cases/structrag/statistical_analysis_use_case.py",
    "StructRAGStatisticalAnalysisUseCase",
)


@pytest.fixture
def router_port():
    return Mock()


@pytest.fixture
def decomposition_port():
    return Mock()


@pytest.fixture
def structurizer_port():
    return Mock()


@pytest.fixture
def training_port():
    return Mock()


@pytest.fixture
def reasoning_port():
    return Mock()


@pytest.fixture
def analysis_port():
    return Mock()


def test_router_use_case_invokes_port(router_port):
    router_port.select_structure.return_value = "graph"
    use_case = StructRAGRouterUseCase(router_port)
    result = use_case.execute(query="q", documents=["doc"], tenant_id="t")
    router_port.select_structure.assert_called_once()
    assert result == "graph"


def test_decomposition_use_case_invokes_port(decomposition_port):
    decomposition_port.decompose_question.return_value = ["sub1"]
    use_case = StructRAGDecompositionUseCase(decomposition_port)
    result = use_case.execute(query="q", documents=["doc"], tenant_id="t")
    decomposition_port.decompose_question.assert_called_once()
    assert result == ["sub1"]


def test_structurizer_use_case_invokes_port(structurizer_port):
    structurizer_port.structurize.return_value = "ok"
    use_case = StructRAGStructurizerUseCase(structurizer_port)
    result = use_case.execute(
        documents=["doc"], structure_type="graph", tenant_id="t", data_id="1"
    )
    structurizer_port.structurize.assert_called_once()
    assert result == "ok"


def test_training_pipeline_use_case_invokes_port(training_port):
    training_port.generate_router_training_data.return_value = []
    use_case = StructRAGTrainingPipelineUseCase(training_port)
    result = use_case.execute(documents=["doc"], tenant_id="t")
    training_port.generate_router_training_data.assert_called_once()
    assert result == []


def test_multi_hop_reasoning_use_case_invokes_port(reasoning_port):
    reasoning_port.answer.return_value = "ans"
    use_case = StructRAGMultiHopReasoningUseCase(reasoning_port)
    result = use_case.execute(query="q", documents=["doc"], tenant_id="t", max_hops=2)
    reasoning_port.answer.assert_called_once()
    assert result == "ans"


def test_statistical_analysis_use_case_invokes_port(analysis_port):
    analysis_port.analyze.return_value = {"answer": "42"}
    use_case = StructRAGStatisticalAnalysisUseCase(analysis_port)
    result = use_case.execute(query="q", documents=["doc"], tenant_id="t")
    analysis_port.analyze.assert_called_once()
    assert result == {"answer": "42"}
