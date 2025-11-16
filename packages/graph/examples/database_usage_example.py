"""Example usage of the database knowledge graph repository.

This example demonstrates how to use the database adapters for storing
and retrieving knowledge graphs with various operations.
"""

import asyncio

from adapters.repositories.database_config import (
    DatabaseConfig,
    create_db_manager,
)
from adapters.repositories.sqlalchemy_knowledge_graph_repository import (
    SQLAlchemyKnowledgeGraphRepository,
)
from application.ports import TracingPort
from application.use_cases.dto import PaginationParams, SortDirection, SortParams
from application.use_cases.list_knowledge_graphs_use_case import (
    KnowledgeGraphFilterParams,
    ListKnowledgeGraphsRequest,
    ListKnowledgeGraphsUseCase,
)
from domain.entities import KnowledgeGraph, ScientificDomain


class MockTracingPort(TracingPort):
    """Mock tracing port for example usage."""

    def start_span(self, name: str, **kwargs):
        """Mock span context manager."""

        class MockSpan:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        return MockSpan()

    def record_metric(self, name: str, value: float, **kwargs):
        """Mock metric recording."""
        import logging

        logging.getLogger(__name__).info(
            "Metric: %s = %s, tags: %s", name, value, kwargs
        )


class MockSubscriptionService:
    """Mock subscription service for example usage."""

    def check_knowledge_graph_limit(self, tenant_id: str) -> None:
        """Mock limit check - always passes."""
        pass


class MockOntologyValidator:
    """Mock ontology validator for example usage."""

    def validate_ontology(self, ontology_id: str) -> bool:
        """Mock validation - always passes."""
        return True


async def main():
    """Main example function demonstrating database operations."""

    import logging

    logger = logging.getLogger(__name__)
    logger.info("\ud83d\ude80 Initializing database...")

    # Initialize database manager and repository
    config = DatabaseConfig.from_env()
    db_manager = create_db_manager(config)
    db_manager.initialize()
    db_manager.create_tables()
    kg_repository = SQLAlchemyKnowledgeGraphRepository(db_manager.get_session())

    # Create mock services
    tracer = MockTracingPort()
    _subscription_service = MockSubscriptionService()
    _ontology_validator = MockOntologyValidator()

    logger.info("\u2705 Database initialized successfully!")

    # Example 1: Create knowledge graphs
    logger.info("\n\ud83d\udcdc Creating sample knowledge graphs...")

    sample_graphs = [
        {
            "name": "Biology Research Graph",
            "domain": ScientificDomain.BIOLOGY,
            "tenant_id": "tenant-001",
            "ontology_version_id": "onto-bio-v1",
            "is_public": False,
        },
        {
            "name": "Chemistry Compounds Database",
            "domain": ScientificDomain.CHEMISTRY,
            "tenant_id": "tenant-001",
            "ontology_version_id": "onto-chem-v1",
            "is_public": True,
        },
        {
            "name": "Physics Concepts Network",
            "domain": ScientificDomain.PHYSICS,
            "tenant_id": "tenant-002",
            "ontology_version_id": "onto-phys-v1",
            "is_public": False,
        },
        {
            "name": "Medical Knowledge Base",
            "domain": ScientificDomain.MEDICINE,
            "tenant_id": "tenant-001",
            "ontology_version_id": "onto-med-v1",
            "is_public": True,
        },
    ]

    created_graphs = []
    for graph_data in sample_graphs:
        # Create knowledge graph entity
        kg = KnowledgeGraph.create(
            name=graph_data["name"],
            tenant_id=graph_data["tenant_id"],
            domain=graph_data["domain"],
            ontology_version_id=graph_data["ontology_version_id"],
            is_public=graph_data["is_public"],
        )

        # Simulate some graph statistics
        kg.update_counts(
            node_count=100 + len(graph_data["name"]) * 10,
            edge_count=200 + len(graph_data["name"]) * 20,
        )

        # Store in database
        created_kg = kg_repository.create(kg)
        created_graphs.append(created_kg)
        print(f"  ✅ Created: {created_kg.name} (ID: {created_kg.id})")

    # Example 2: List knowledge graphs with pagination
    print("\n📋 Listing knowledge graphs with pagination...")

    list_use_case = ListKnowledgeGraphsUseCase(
        kg_repository=kg_repository, tracer=tracer
    )

    # Basic listing for tenant-001
    request = ListKnowledgeGraphsRequest(
        tenant_id="tenant-001",
        user_id="user-001",
        pagination=PaginationParams(page=1, page_size=10),
    )

    response = await list_use_case.execute(request)

    if response.success and response.knowledge_graphs:
        print(f"  📊 Found {response.knowledge_graphs.total_items} knowledge graphs")
        print(
            f"  📄 Page {response.knowledge_graphs.page} of {response.knowledge_graphs.total_pages}"
        )

        for kg_dto in response.knowledge_graphs.items:
            print(
                f"    - {kg_dto.name} ({kg_dto.domain}) - Nodes: {kg_dto.node_count}, Edges: {kg_dto.edge_count}"
            )

    # Example 3: Filtering by domain
    print("\n🔍 Filtering by domain (Biology)...")

    filters = KnowledgeGraphFilterParams(domain=ScientificDomain.BIOLOGY)

    filtered_request = ListKnowledgeGraphsRequest(
        tenant_id="tenant-001",
        user_id="user-001",
        pagination=PaginationParams(page=1, page_size=10),
        filters=filters,
    )

    filtered_response = await list_use_case.execute(filtered_request)

    if filtered_response.success and filtered_response.knowledge_graphs:
        print(
            f"  🧬 Found {filtered_response.knowledge_graphs.total_items} biology graphs"
        )
        for kg_dto in filtered_response.knowledge_graphs.items:
            print(f"    - {kg_dto.name} ({kg_dto.domain})")

    # Example 4: Filtering by public visibility
    print("\n🌐 Filtering by public visibility...")

    public_filters = KnowledgeGraphFilterParams(is_public=True)

    public_request = ListKnowledgeGraphsRequest(
        tenant_id="tenant-001",
        user_id="user-001",
        pagination=PaginationParams(page=1, page_size=10),
        filters=public_filters,
    )

    public_response = await list_use_case.execute(public_request)

    if public_response.success and public_response.knowledge_graphs:
        print(
            f"  🔓 Found {public_response.knowledge_graphs.total_items} public graphs"
        )
        for kg_dto in public_response.knowledge_graphs.items:
            print(f"    - {kg_dto.name} (Public: {kg_dto.is_public})")

    # Example 5: Sorting by node count
    print("\n📊 Sorting by node count (descending)...")

    sort_params = SortParams(sort_by="node_count", direction=SortDirection.DESC)

    sorted_request = ListKnowledgeGraphsRequest(
        tenant_id="tenant-001",
        user_id="user-001",
        pagination=PaginationParams(page=1, page_size=10),
        sort=sort_params,
    )

    sorted_response = await list_use_case.execute(sorted_request)

    if sorted_response.success and sorted_response.knowledge_graphs:
        print(
            f"  📈 Sorted {sorted_response.knowledge_graphs.total_items} graphs by node count"
        )
        for kg_dto in sorted_response.knowledge_graphs.items:
            print(f"    - {kg_dto.name}: {kg_dto.node_count} nodes")

    # Example 6: Complex filtering
    print("\n🔬 Complex filtering (Chemistry + Public + Min 100 nodes)...")

    complex_filters = KnowledgeGraphFilterParams(
        domain=ScientificDomain.CHEMISTRY, is_public=True, min_node_count=100
    )

    complex_request = ListKnowledgeGraphsRequest(
        tenant_id="tenant-001",
        user_id="user-001",
        pagination=PaginationParams(page=1, page_size=10),
        filters=complex_filters,
    )

    complex_response = await list_use_case.execute(complex_request)

    if complex_response.success and complex_response.knowledge_graphs:
        print(
            f"  ⚗️ Found {complex_response.knowledge_graphs.total_items} matching graphs"
        )
        for kg_dto in complex_response.knowledge_graphs.items:
            print(
                f"    - {kg_dto.name}: {kg_dto.node_count} nodes, Public: {kg_dto.is_public}"
            )

    # Example 7: Retrieve specific knowledge graph
    print("\n🔍 Retrieving specific knowledge graph...")

    if created_graphs:
        first_kg = created_graphs[0]
        retrieved_kg = kg_repository.get_by_id(first_kg.id, first_kg.tenant_id)

        if retrieved_kg:
            print(f"  ✅ Retrieved: {retrieved_kg.name}")
            print(f"    - ID: {retrieved_kg.id}")
            print(f"    - Domain: {retrieved_kg.domain.value}")
            print(f"    - Created: {retrieved_kg.created_at}")
            print(
                f"    - Nodes: {retrieved_kg.node_count}, Edges: {retrieved_kg.edge_count}"
            )

    # Example 8: Update knowledge graph
    print("\n✏️ Updating knowledge graph...")

    if created_graphs:
        kg_to_update = created_graphs[0]
        kg_to_update.update_counts(node_count=1500, edge_count=3000)
        kg_to_update.set_public(True)

        updated_kg = kg_repository.update(kg_to_update)
        print(f"  ✅ Updated: {updated_kg.name}")
        print(f"    - New node count: {updated_kg.node_count}")
        print(f"    - New edge count: {updated_kg.edge_count}")
        print(f"    - Now public: {updated_kg.is_public}")

    print("\n🎉 Database operations completed successfully!")
    print("\n💡 Key Features Demonstrated:")
    print("  ✅ Knowledge graph creation and storage")
    print("  ✅ Pagination with configurable page sizes")
    print("  ✅ Filtering by domain, visibility, and node counts")
    print("  ✅ Sorting by various fields")
    print("  ✅ Complex multi-criteria filtering")
    print("  ✅ Individual graph retrieval")
    print("  ✅ Graph updates with statistics")
    print("  ✅ Multi-tenant isolation")


if __name__ == "__main__":
    asyncio.run(main())
