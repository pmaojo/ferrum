"""Locust load testing for GraphRAG Ontology Application.

This file defines Locust load tests for system stress testing and clustering performance.
To run: locust -f tests/performance/locustfile.py
"""

import json
import logging
import random
import os
from locust import HttpUser, task, between


class GraphRAGUser(HttpUser):
    """Simulated user for GraphRAG API load testing."""

    wait_time = between(1, 5)  # Wait between 1-5 seconds between tasks

    def on_start(self):
        """Initialize user session."""
        # Set tenant ID and authentication
        self.tenant_id = f"tenant_{random.randint(1, 10)}"
        self.headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": self.tenant_id,
            "Authorization": f"Bearer {os.environ.get('TEST_API_KEY', 'test_key')}"
        }

        # Pre-defined knowledge graph IDs
        self.kg_ids = [f"kg_{i}" for i in range(1, 6)]

        # Sample questions for querying
        self.questions = [
            "Who works at TechCorp?",
            "What products does TechCorp offer?",
            "How is the engineering team structured?",
            "What is the relationship between Alice and CloudSuite?",
            "Which departments exist at TechCorp?",
            "Who manages the engineering team?",
            "What technologies are used in CloudSuite?",
            "When was TechCorp founded?",
            "How many employees work at TechCorp?",
            "What is the main business of TechCorp?"
        ]

    @task(3)
    def query_knowledge_graph(self):
        """Execute natural language query against knowledge graph."""
        kg_id = random.choice(self.kg_ids)
        question = random.choice(self.questions)

        payload = {
            "question": question,
            "kg_id": kg_id,
            "opts": {
                "max_hops": random.choice([1, 2, 3]),
                "include_reasoning": random.choice([True, False]),
                "return_triples": random.choice([True, False])
            }
        }

        with self.client.post(
            "/api/v1/query",
            json=payload,
            headers=self.headers,
            name="Query Knowledge Graph",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                # Check for valid response structure
                try:
                    data = response.json()
                    if "results" not in data:
                        response.failure("Missing results in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Query failed with status {response.status_code}")

    @task(1)
    def index_document(self):
        """Index a document into the knowledge graph."""
        kg_id = random.choice(self.kg_ids)

        # Generate random document content
        companies = ["TechCorp", "GlobalSoft", "DataTech", "CloudSystems", "SecureNet"]
        people = ["Alice", "Bob", "Charlie", "Diana", "Edward", "Fiona", "George"]
        roles = ["Software Engineer", "Product Manager", "Data Scientist",
                "DevOps Engineer", "UX Designer", "QA Engineer"]
        products = ["CloudSuite", "DataAnalyzer", "SecureConnect",
                   "DevPortal", "AIAssistant", "MobileFramework"]

        company = random.choice(companies)
        person1 = random.choice(people)
        person2 = random.choice(people)
        role1 = random.choice(roles)
        role2 = random.choice(roles)
        product = random.choice(products)

        document = f"""
        {company} is a technology company in the software industry.
        {person1} works at {company} as a {role1}.
        {person2} works at {company} as a {role2}.
        {person1} is working on the {product} project.
        The {product} is one of {company}'s main products.
        """

        payload = {
            "documents": [document],
            "kg_id": kg_id
        }

        with self.client.post(
            "/api/v1/index",
            json=payload,
            headers=self.headers,
            name="Index Document",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "triples_count" not in data:
                        response.failure("Missing triples_count in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Indexing failed with status {response.status_code}")

    @task(2)
    def visualize_graph(self):
        """Request graph visualization."""
        kg_id = random.choice(self.kg_ids)

        with self.client.get(
            f"/api/v1/visualize/{kg_id}",
            headers=self.headers,
            name="Visualize Graph",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "nodes" not in data or "edges" not in data:
                        response.failure("Missing nodes or edges in visualization")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Visualization failed with status {response.status_code}")

    @task(1)
    def get_community_detail(self):
        """Request community detail for progressive loading."""
        kg_id = random.choice(self.kg_ids)
        community_id = f"{kg_id}:{random.randint(1, 5)}"

        with self.client.get(
            f"/api/v1/community/{community_id}",
            headers=self.headers,
            name="Get Community Detail",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "nodes" not in data or "edges" not in data:
                        response.failure("Missing nodes or edges in community detail")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                # Community might not exist, so log and treat 404 as a successful response
                logging.info("Community %s not found; treated as valid case", community_id)
                response.success()
            else:
                response.failure(f"Community detail failed with status {response.status_code}")

    @task(1)
    def validate_ontology(self):
        """Validate triples against ontology."""
        kg_id = random.choice(self.kg_ids)
        ontology_version_id = f"onto_v{random.randint(1, 3)}"

        # Generate random triples for validation
        entity_types = ["Person", "Company", "Product", "Team", "Role"]
        predicates = ["worksAt", "manages", "develops", "partOf", "hasRole"]

        triples = []
        for _ in range(random.randint(3, 10)):
            subject_type = random.choice(entity_types)
            subject = f"{subject_type}_{random.randint(1, 100)}"
            predicate = random.choice(predicates)
            object_type = random.choice(entity_types)
            object = f"{object_type}_{random.randint(1, 100)}"

            triples.append({
                "subject": subject,
                "predicate": predicate,
                "object": object
            })

        payload = {
            "triples": triples,
            "kg_id": kg_id,
            "ontology_version_id": ontology_version_id
        }

        with self.client.post(
            "/api/v1/validate",
            json=payload,
            headers=self.headers,
            name="Validate Ontology",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "is_consistent" not in data:
                        response.failure("Missing is_consistent in validation response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Validation failed with status {response.status_code}")


class WebSocketUser(HttpUser):
    """Simulated user for WebSocket graph stream testing."""

    wait_time = between(5, 15)  # Wait longer between WebSocket connections

    def on_start(self):
        """Initialize user session."""
        self.tenant_id = f"tenant_{random.randint(1, 10)}"
        self.headers = {
            "X-Tenant-ID": self.tenant_id,
            "Authorization": f"Bearer {os.environ.get('TEST_API_KEY', 'test_key')}"
        }
        self.kg_ids = [f"kg_{i}" for i in range(1, 6)]

    @task
    def connect_to_graph_stream(self):
        """Connect to graph stream WebSocket."""
        kg_id = random.choice(self.kg_ids)

        # Note: Locust doesn't natively support WebSockets
        # This is a placeholder that simulates the WebSocket connection
        # by making a regular HTTP request to the WebSocket endpoint
        with self.client.get(
            f"/api/v1/stream/{kg_id}/connect",
            headers=self.headers,
            name="Connect to Graph Stream",
            catch_response=True
        ) as response:
            if response.status_code == 101:  # WebSocket switching protocols
                logging.info("WebSocket upgrade for %s succeeded", kg_id)
                response.success()
                # WebSocket upgrade succeeded; mark the request as successful
            else:
                response.failure(f"WebSocket connection failed with status {response.status_code}")


# To run this test:
# 1. Install locust: pip install locust
# 2. Run: locust -f tests/performance/locustfile.py
# 3. Open http://localhost:8089 in your browser
# 4. Configure the test parameters and start the test
