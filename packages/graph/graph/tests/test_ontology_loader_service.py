import unittest
from unittest.mock import MagicMock

from domain.hybrid_reasoning import OntologyLoaderService


class TestOntologyLoaderService(unittest.TestCase):
    def test_load_uses_world(self):
        world = MagicMock()
        ontology = MagicMock()
        world.get_ontology.return_value = ontology
        ontology.load.return_value = ontology

        service = OntologyLoaderService(world=world)
        result = service.load(path="/path/onto.owl")

        world.get_ontology.assert_called_with("/path/onto.owl")
        ontology.load.assert_called_once()
        assert result is ontology


if __name__ == "__main__":
    unittest.main()
