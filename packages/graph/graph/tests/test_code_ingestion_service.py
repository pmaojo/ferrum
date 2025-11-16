import logging
import pytest
pytest.importorskip("PIL")
pytest.importorskip("numpy")
from unittest.mock import Mock

from adapters.python_ast_analyzer_adapter import PythonASTAnalyzerAdapter
from domain.code_ingestion_service import CodeIngestionService
from domain.services import IngestionService
from application.ports import GraphRetrieverPort, OntologyValidatorPort
from domain.entities import Triple, ValidationReport


class TestPythonASTAnalyzerAdapter:
    def test_extract_triples(self):
        code = """\nclass Foo:\n    def bar(self):\n        pass\n\ndef baz():\n    return True\n"""
        adapter = PythonASTAnalyzerAdapter()
        triples = adapter.extract_triples(code=code, repo_id="repo1", tenant_id="t1")
        assert Triple("repo1", "definesClass", "Foo", "t1") in triples
        assert Triple("Foo", "hasMethod", "bar", "t1") in triples
        assert Triple("repo1", "definesFunction", "baz", "t1") in triples


class TestCodeIngestionService:
    @pytest.fixture
    def ingestion_service(self) -> IngestionService:
        retriever = Mock(spec=GraphRetrieverPort)
        validator = Mock(spec=OntologyValidatorPort)
        service = IngestionService(
            retriever=retriever,
            validator=validator,
            tracer=None,
            logger=logging.getLogger("test.ingestion_service"),
        )
        return service

    def test_ingest_repository(self, ingestion_service: IngestionService):
        analyzer = PythonASTAnalyzerAdapter()
        service = CodeIngestionService(
            analyzer=analyzer, ingestion_service=ingestion_service
        )

        repo_files = {"a.py": "def foo():\n    pass"}
        validation = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id="t1",
            ontology_version_id="v1",
        )
        ingestion_service.validate_triples = Mock(return_value=validation)
        expected_triples = list(
            service.stream_ingest_repository(
                files_iterable=repo_files.values(),
                repo_id="repo1",
                tenant_id="t1",
            )
        )

        service.stream_ingest_repository = Mock(
            return_value=iter(expected_triples)
        )

        result = service.ingest_repository(
            files=repo_files,
            repo_id="repo1",
            tenant_id="t1",
            ontology_version_id="v1",
        )

        assert result == validation
        assert service.stream_ingest_repository.call_count == 1
        called_args = service.stream_ingest_repository.call_args.kwargs
        assert list(called_args["files_iterable"]) == list(repo_files.values())
        assert called_args["repo_id"] == "repo1"
        assert called_args["tenant_id"] == "t1"
        ingestion_service.validate_triples.assert_called_once_with(
            triples=expected_triples,
            ontology_version_id="v1",
            tenant_id="t1",
            validate_incrementally=True,
        )

    def test_stream_ingest_repository_yields_incrementally(
        self, ingestion_service: IngestionService
    ):
        analyzer = Mock(spec=PythonASTAnalyzerAdapter)
        triples = [
            Triple("repo", "p1", "o1", "t1"),
            Triple("repo", "p2", "o2", "t1"),
        ]
        analyzer.extract_triples.side_effect = [[triples[0]], [triples[1]]]
        service = CodeIngestionService(
            analyzer=analyzer, ingestion_service=ingestion_service
        )

        yielded = []

        def file_source():
            for idx in range(2):
                yielded.append(idx)
                yield f"code{idx}"

        gen = service.stream_ingest_repository(
            files_iterable=file_source(),
            repo_id="repo",
            tenant_id="t1",
        )

        first = next(gen)
        assert first == triples[0]
        assert yielded == [0]
        second = next(gen)
        assert second == triples[1]
        assert yielded == [0, 1]
        with pytest.raises(StopIteration):
            next(gen)
        assert yielded == [0, 1]

