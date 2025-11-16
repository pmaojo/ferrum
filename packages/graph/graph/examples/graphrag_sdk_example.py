#!/usr/bin/env python3
"""
Example demonstrating proper FalkorDB GraphRAG SDK integration.

This example shows how to use the GraphRAG SDK with ontology files:
1. Create and load ontology from JSON file
2. Index documents with ontology support
3. Query the knowledge graph using natural language

Run with: python examples/graphrag_sdk_example.py
"""

import os
import json
import asyncio
from adapters.retrievers.graphrag_sdk_adapter import GraphRAGSDKAdapter
from domain.services import GraphRAGException

async def main():
    """Run GraphRAG SDK example with ontology support."""
    print("🚀 GraphRAG SDK Integration Example with Ontology")
    print("=" * 55)

    # Initialize the GraphRAG SDK adapter
    try:
        adapter = GraphRAGSDKAdapter(
            host=os.getenv("FALKORDB_HOST", "127.0.0.1"),
            port=int(os.getenv("FALKORDB_PORT", "6379")),
            username=os.getenv("FALKORDB_USER"),
            password=os.getenv("FALKORDB_PASSWORD"),
            llm_model="gemini-2.5-flash",
            api_key=os.getenv("GEMINI_API_KEY")
        )
        print("✅ GraphRAG SDK adapter initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize adapter: {e}")
        return

    # Step 1: Create ontology file (this follows GraphRAG SDK pattern)
    print("\n📋 Creating Ontology File")
    print("-" * 30)

    try:
        ontology_file = adapter.create_ontology_file(
            entities=["Technology", "Database", "Framework", "Agent", "Capability"],
            relationships=["uses", "supports", "enables", "integrates_with", "provides"],
            output_file="ontology.json"
        )
        print(f"✅ Created ontology file: {ontology_file}")

        # Show ontology content
        with open(ontology_file, "r") as f:
            ontology_content = json.loads(f.read())
            print(f"📊 Entities: {len(ontology_content['entities'])}")
            print(f"📊 Relationships: {len(ontology_content['relationships'])}")

    except Exception as e:
        print(f"❌ Failed to create ontology: {e}")
        return

    # Example documents to index
    documents = [
        """
        GraphRAG is a powerful framework for building knowledge graphs from unstructured text.
        It combines graph databases with retrieval-augmented generation to provide accurate answers.
        The technology can extract entities, relationships, and concepts from documents automatically.
        GraphRAG uses advanced machine learning capabilities to understand document content.
        """,
        """
        FalkorDB is a high-performance graph database that supports both property graphs and RDF.
        The database provides real-time analytics capabilities for complex graph operations.
        FalkorDB integrates with various frameworks to enable scalable graph processing.
        This technology supports advanced querying and supports multi-tenant architectures.
        """,
        """
        Multi-agent systems enable autonomous software agents to collaborate on complex tasks.
        These agents use knowledge graphs to share information and coordinate workflows.
        Agent frameworks provide capabilities for distributed problem solving and decision making.
        The technology integrates with databases to enable intelligent data processing workflows.
        """
    ]

    # Step 2: Index documents with ontology (following GraphRAG SDK pattern)
    print("\n📚 Indexing Documents with Ontology")
    print("-" * 40)

    try:
        # This follows the exact pattern: kg.process_sources(sources)
        triples = adapter.index(
            docs=documents,
            kg_id="example_kg",
            tenant_id="example_tenant",
            ontology_file=ontology_file  # Load ontology from disk
        )
        print(f"✅ Indexed {len(documents)} documents with ontology")
        print(f"📊 Extracted {len(triples)} triples")

        # Show some example triples
        for i, triple in enumerate(triples[:5]):
            print(f"   {i+1}. {triple.subject} → {triple.predicate} → {triple.object}")
        if len(triples) > 5:
            print(f"   ... and {len(triples) - 5} more triples")

    except GraphRAGException as e:
        print(f"❌ Indexing failed: {e.message}")
        return

    # Step 3: Query the knowledge graph (using kg.ask() method)
    print("\n🔍 Querying Knowledge Graph with GraphRAG SDK")
    print("-" * 50)

    queries = [
        "What technologies are mentioned in the documents?",
        "How does GraphRAG work with databases?",
        "What capabilities do agents have?",
        "Which frameworks integrate with FalkorDB?",
        "Tell me about the relationships between different technologies"
    ]

    for query in queries:
        print(f"\n❓ Query: {query}")
        try:
            # This uses the SDK's kg.ask() method internally
            result = adapter.run(
                question=query,
                kg_id="example_kg",
                tenant_id="example_tenant",
                opts={
                    "return_formatted": True,
                    "include_reasoning": True,
                    "include_metadata": True
                }
            )

            if isinstance(result, dict):
                print(f"💡 Answer: {result.get('answer', 'No answer provided')}")
                if result.get('explanation'):
                    print(f"🧠 Reasoning: {result['explanation']}")
                if result.get('metadata'):
                    print(f"⏱️  Execution: {result['metadata']['execution_time_ms']:.2f}ms")
                    print(f"📊 Results: {result['metadata']['result_count']} items")
            else:
                print(f"💡 Answer: {result}")

        except GraphRAGException as e:
            print(f"❌ Query failed: {e.message}")

    print("\n🎉 GraphRAG SDK Example completed successfully!")
    print("\n💡 Key Features Demonstrated:")
    print("   1. ✅ Ontology creation and loading from JSON file")
    print("   2. ✅ Document processing with kg.process_sources()")
    print("   3. ✅ Natural language querying with kg.ask()")
    print("   4. ✅ Proper GraphRAG SDK integration pattern")
    print("\n🚀 Next Steps:")
    print("   1. Customize your ontology with domain-specific entities")
    print("   2. Add more sophisticated relationship types")
    print("   3. Integrate with your multi-agent workflows")
    print("   4. Scale with FalkorDB's high-performance capabilities")

if __name__ == "__main__":
    asyncio.run(main())
