from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from domain.services import GraphRAGException

logger = logging.getLogger(__name__)


class KnowledgeGraphManager:
    """Create and cache knowledge graphs."""

    def __init__(
        self,
        sdk: Dict[str, Any],
        host: str,
        port: int,
        username: Optional[str],
        password: Optional[str],
    ) -> None:
        self._sdk = sdk
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._knowledge_graphs: Dict[str, Any] = {}

    def get_or_create(
        self, kg_id: str, tenant_id: str, ontology_file: Optional[str] = None
    ) -> Any:
        kg_key = f"{tenant_id}_{kg_id}"
        if kg_key in self._knowledge_graphs:
            return self._knowledge_graphs[kg_key]

        try:
            ontology = None
            if ontology_file and os.path.exists(ontology_file):
                with open(ontology_file, "r", encoding="utf-8") as file:
                    ontology_data = json.loads(file.read())
                    ontology = self._sdk["Ontology"].from_json(ontology_data)

            kg_config = {
                "name": kg_key,
                "model_config": self._sdk["KnowledgeGraphModelConfig"].with_model(
                    self._sdk["model"]
                ),
                "host": self._host,
                "port": self._port,
            }
            if ontology:
                kg_config["ontology"] = ontology
            if self._username:
                kg_config["username"] = self._username
            if self._password:
                kg_config["password"] = self._password

            kg = self._sdk["KnowledgeGraph"](**kg_config)
            self._knowledge_graphs[kg_key] = kg
            logger.info("Created knowledge graph: %s", kg_key)
            return kg
        except Exception as e:
            logger.error("Failed to create knowledge graph %s: %s", kg_key, e)
            raise GraphRAGException(
                message=f"Knowledge graph creation failed: {str(e)}",
                error_code="KG_CREATION_ERROR",
                context={"kg_id": kg_id, "tenant_id": tenant_id},
            ) from e

    @staticmethod
    def create_ontology_file(
        entities: List[str],
        relationships: List[str],
        output_file: str = "ontology.json",
    ) -> str:
        try:
            ontology_data = {
                "entities": [{"name": e, "type": "entity"} for e in entities],
                "relationships": [
                    {"name": r, "type": "relationship"} for r in relationships
                ],
            }
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(ontology_data, f, indent=2)
            logger.info("Created ontology file: %s", output_file)
            return output_file
        except Exception as e:
            logger.error("Failed to create ontology file: %s", e)
            raise GraphRAGException(
                message=f"Ontology file creation failed: {str(e)}",
                error_code="ONTOLOGY_CREATION_ERROR",
                context={"output_file": output_file},
            ) from e
