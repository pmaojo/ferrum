from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

import requests

from application.ports import OntologyLoaderPort
from domain.entities import OntologyVersion, ScientificDomain

logger = logging.getLogger(__name__)


class OwlOntologyLoader(OntologyLoaderPort):
    """Load official OWL ontologies from various sources."""

    # Official ontology repositories
    ONTOLOGY_SOURCES = {
        "bioontology": "https://bioportal.bioontology.org/ontologies/",
        "fao": "https://www.fao.org/aims/aos/",
        "agrovoc": "https://agrovoc.fao.org/browse/",
        "plant_ontology": "https://planteome.org/",
        "trait_ontology": "https://www.cropontology.org/",
    }

    # Pre-configured permaculture/agriculture ontologies
    AGRICULTURE_ONTOLOGIES = {
        "plant_ontology": {
            "url": "http://purl.obolibrary.org/obo/po.owl",
            "description": "Plant Ontology - anatomical and morphological structures",
        },
        "crop_ontology": {
            "url": "http://www.cropontology.org/ontology/CO_715.owl",
            "description": "Crop Ontology - traits, phenotypes, and breeding",
        },
        "agrovoc": {
            "url": "https://agrovoc.fao.org/agrovoc.owl",
            "description": "FAO's multilingual vocabulary for agriculture",
        },
        "peco": {
            "url": "http://purl.obolibrary.org/obo/peco.owl",
            "description": "Plant Experimental Conditions Ontology",
        },
    }

    def __init__(self, cache_dir: str = "./cache/ontologies"):
        self.cache_dir = cache_dir
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        import os

        os.makedirs(self.cache_dir, exist_ok=True)

    def load_official_ontology(
        self, *, ontology_name: str, tenant_id: str, force_refresh: bool = False
    ) -> OntologyVersion:
        """Load an official ontology by name."""

        if ontology_name not in self.AGRICULTURE_ONTOLOGIES:
            available = ", ".join(self.AGRICULTURE_ONTOLOGIES.keys())
            raise ValueError(
                f"Unknown ontology: {ontology_name}. Available: {available}"
            )

        ontology_config = self.AGRICULTURE_ONTOLOGIES[ontology_name]
        url = ontology_config["url"]

        logger.info(f"Loading official ontology: {ontology_name} from {url}")

        # Check cache first
        cache_path = f"{self.cache_dir}/{ontology_name}.owl"
        if not force_refresh and self._is_cached(cache_path):
            axioms = self._load_from_cache(cache_path)
        else:
            axioms = self._download_and_parse_owl(url)
            self._save_to_cache(cache_path, axioms)

        return OntologyVersion.create(
            tenant_id=tenant_id,
            domain=ScientificDomain.AGRICULTURE,
            axioms=axioms,
            metadata={
                "source": "official",
                "ontology_name": ontology_name,
                "description": ontology_config["description"],
                "url": url,
            },
        )

    def _is_cached(self, cache_path: str) -> bool:
        """Check if ontology is cached and not too old."""
        import os
        from datetime import datetime, timedelta

        if not os.path.exists(cache_path):
            return False

        # Consider cached for 24 hours
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        return datetime.now() - file_time < timedelta(hours=24)

    def _load_from_cache(self, cache_path: str) -> List[str]:
        """Load axioms from cached file."""
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            logger.warning(f"Failed to load from cache: {e}")
            return []

    def _save_to_cache(self, cache_path: str, axioms: List[str]) -> None:
        """Save axioms to cache file."""
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                for axiom in axioms:
                    f.write(axiom + "\n")
        except Exception as e:
            logger.warning(f"Failed to save to cache: {e}")

    def _download_and_parse_owl(self, url: str) -> List[str]:
        """Download and parse OWL ontology from URL."""
        try:
            logger.info(f"Downloading ontology from {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse OWL/RDF XML
            root = ET.fromstring(response.content)
            axioms = self._extract_axioms_from_owl(root)

            logger.info(f"Successfully parsed {len(axioms)} axioms")
            return axioms

        except Exception as e:
            logger.error(f"Failed to download/parse ontology from {url}: {e}")
            # Return basic fallback axioms
            return self._get_fallback_axioms()

    def _extract_axioms_from_owl(self, root: ET.Element) -> List[str]:
        """Extract Manchester syntax axioms from OWL XML."""
        axioms = []

        # Define XML namespaces commonly used in OWL
        namespaces = {
            "owl": "http://www.w3.org/2002/07/owl#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        }

        # Extract classes
        for cls in root.findall(".//owl:Class", namespaces):
            about = cls.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about")
            if about:
                class_name = self._extract_name_from_uri(about)
                axioms.append(f"Class: {class_name}")

        # Extract object properties
        for prop in root.findall(".//owl:ObjectProperty", namespaces):
            about = prop.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about")
            if about:
                prop_name = self._extract_name_from_uri(about)
                axioms.append(f"ObjectProperty: {prop_name}")

        # Extract data properties
        for prop in root.findall(".//owl:DatatypeProperty", namespaces):
            about = prop.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about")
            if about:
                prop_name = self._extract_name_from_uri(about)
                axioms.append(f"DataProperty: {prop_name}")

        return axioms

    def _extract_name_from_uri(self, uri: str) -> str:
        """Extract the local name from a URI."""
        if "#" in uri:
            return uri.split("#")[-1]
        elif "/" in uri:
            return uri.split("/")[-1]
        return uri

    def _get_fallback_axioms(self) -> List[str]:
        """Provide fallback axioms for permaculture when download fails."""
        return [
            "Class: Plant",
            "Class: Soil",
            "Class: Nutrient",
            "Class: Nitrogen",
            "Class: Phosphorus",
            "Class: Potassium",
            "ObjectProperty: fixes_nitrogen",
            "ObjectProperty: depletes_nitrogen",
            "ObjectProperty: requires_nutrient",
            "ObjectProperty: companion_with",
            "ObjectProperty: incompatible_with",
            "ClassAssertion: Plant Legume",
            "ClassAssertion: Plant Tomato",
            "ClassAssertion: Plant Corn",
            "ObjectPropertyAssertion: fixes_nitrogen Legume Nitrogen",
            "ObjectPropertyAssertion: depletes_nitrogen Tomato Nitrogen",
            "ObjectPropertyAssertion: companion_with Legume Tomato",
        ]

    def list_available_ontologies(self) -> Dict[str, Any]:
        """List all available official ontologies."""
        return {
            name: {
                "description": config["description"],
                "url": config["url"],
                "domain": "agriculture",
            }
            for name, config in self.AGRICULTURE_ONTOLOGIES.items()
        }
