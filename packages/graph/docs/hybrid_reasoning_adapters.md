# Hybrid Reasoning Adapters

This document describes the reference implementations of the ports defined in
`application/ports/hybrid_reasoning.py`.  Each adapter exposes a small piece of
functionality that can be swapped with more sophisticated components in the
future.

## FileOntologyLoaderAdapter

* **Input:** `path` – file system path to an OWL ontology.
* **Output:** Loaded ontology object (owlready2 ontology or raw text).

## BasicConsistencyCheckerAdapter

* **Input:**
  * `triples` – list of `domain.entities.Triple` instances.
  * `ontology_version_id` – identifier for the ontology version.
* **Output:** `domain.entities.ValidationReport` with one violation per triple
  missing any of the subject, predicate or object fields.

## SimpleReasoningExplanationAdapter

* **Input:**
  * `report` – validation report to summarise.
  * `llm_output` – text produced by an LLM answering the question.
  * `tenant_id` – identifier of the tenant requesting the explanation.
* **Output:** Human readable explanation string combining the above data.

## RegexEntityLinkingAdapter

* **Input:**
  * `text` – free text containing entities.
  * `ontology` – ontology object or IRI used to build entity IRIs.
  * `tenant_id` – identifier of the tenant.
* **Output:** List of ontology IRIs for entities extracted from the text.

## SimpleHybridReasoningAdapter

* **Input:**
  * `question` – natural language question.
  * `triples` – triples to validate.
  * `ontology_version_id` – identifier or path of the ontology.
  * `tenant_id` – identifier of the tenant.
* **Output:** Dictionary with:
  * `links` – entity IRIs linked from the question.
  * `validation` – `ValidationReport` returned by the checker.
  * `explanation` – natural language explanation of the reasoning.

These adapters are intentionally lightweight and primarily serve as examples for
how the ports can be wired together in a hybrid reasoning system.
