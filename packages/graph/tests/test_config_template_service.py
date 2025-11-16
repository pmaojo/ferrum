import inspect
from unittest.mock import Mock

import pytest
import yaml

from application.services.config_template_service import ConfigTemplateService

import json

import application.services.config_template_service as cts

from application.ports.configuration import ConfigurationScope


class TestConfigTemplateService:
    def test_generate_yaml_success(self):
        llm = Mock()
        llm.generate.side_effect = ["graphrag_sdk:\n  host: 0.0.0.0", "ontology: {}", "workflow: {}"]
        config_port = Mock()
        config_port.validate_configuration.return_value = []

        service = ConfigTemplateService(llm=llm, configuration_port=config_port)
        yaml_text = service.generate_yaml("t1")
        data = yaml.safe_load(yaml_text)

        assert data["graphrag_sdk"]["host"] == "0.0.0.0"
        config_port.validate_configuration.assert_called_once_with(ConfigurationScope.TENANT, data)

    def test_validation_error(self):
        llm = Mock()
        llm.generate.return_value = "graphrag_sdk: {}"
        config_port = Mock()
        config_port.validate_configuration.return_value = ["error"]

        service = ConfigTemplateService(llm=llm, configuration_port=config_port)
        with pytest.raises(ValueError):
            service.generate_yaml("t1")

    def test_malformed_yaml_returns_empty_dict(self, caplog):
        llm = Mock()
        llm.generate.return_value = "graphrag_sdk: ["
        config_port = Mock()
        service = ConfigTemplateService(llm=llm, configuration_port=config_port)

        with caplog.at_level("ERROR"):
            result = service._ask("q", "tenant")

        assert result == {}
        assert any("Failed to parse YAML" in r.message for r in caplog.records)

    def test_docstrings_present(self):
        assert "question" in inspect.getdoc(ConfigTemplateService._ask)
        assert "tenant_id" in inspect.getdoc(ConfigTemplateService.assemble_configuration)
        assert "tenant_id" in inspect.getdoc(ConfigTemplateService.generate_yaml)
    def test_list_templates_multiple_extensions(self, tmp_path, monkeypatch):
        """Ensure JSON and YAML templates are detected."""
        # Create sample templates
        (tmp_path / "sample.json").write_text(json.dumps({"a": 1}), encoding="utf-8")
        (tmp_path / "sample.yaml").write_text("b: 2", encoding="utf-8")
        (tmp_path / "sample.yml").write_text("c: 3", encoding="utf-8")

        # Patch templates root to temporary directory
        monkeypatch.setattr(cts, "TEMPLATES_ROOT", tmp_path)

        templates = cts.list_templates()
        assert set(templates) == {"sample.json", "sample.yaml", "sample.yml"}

        # Verify loading works for both formats
        assert cts.load_template("sample.json") == {"a": 1}
        assert cts.load_template("sample.yaml") == {"b": 2}
        assert cts.load_template("sample.yml") == {"c": 3}
