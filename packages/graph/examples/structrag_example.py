
"""Example demonstrating StructRAG usage for knowledge-intensive reasoning."""

import asyncio
import logging
import os
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import necessary components
from adapters.llm.gemini_llm_adapter import GeminiLLMAdapter
from adapters.structrag_adapter import StructRAGAdapter
from adapters.inmemory_tracing_adapter import InMemoryTracingAdapter
from application.use_cases.structrag.query_with_structrag_use_case import (
    QueryWithStructRAGUseCase,
    IndexDocumentsWithStructRAGUseCase,
)


def create_sample_documents():
    """Create sample documents for StructRAG demonstration."""
    return [
        """Machine Learning Fundamentals

Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data. There are three main types of machine learning: supervised learning, unsupervised learning, and reinforcement learning.

Supervised learning uses labeled training data to learn a mapping from inputs to outputs. Common algorithms include linear regression, decision trees, and neural networks. Applications include image classification, spam detection, and medical diagnosis.

Unsupervised learning finds patterns in data without labeled examples. Clustering algorithms like K-means group similar data points, while dimensionality reduction techniques like PCA simplify complex datasets.

Reinforcement learning trains agents to make decisions through trial and error, receiving rewards or penalties. This approach has achieved breakthroughs in game playing (AlphaGo) and robotics.""",

        """Deep Learning Architecture Types

Neural Network Types and Applications:

1. Feedforward Neural Networks
   - Basic architecture with layers of connected neurons
   - Applications: Simple classification tasks
   - Limitations: Cannot handle sequential data

2. Convolutional Neural Networks (CNNs)
   - Specialized for image processing
   - Key components: Convolution layers, pooling layers, activation functions
   - Applications: Computer vision, medical imaging, autonomous vehicles

3. Recurrent Neural Networks (RNNs)
   - Designed for sequential data
   - Variants: LSTM, GRU
   - Applications: Natural language processing, time series prediction

4. Transformer Architecture
   - Attention-based model
   - Breakthrough in language understanding
   - Applications: GPT, BERT, machine translation

Performance Metrics:
- Accuracy: Overall correctness
- Precision: True positives / (True positives + False positives)
- Recall: True positives / (True positives + False negatives)
- F1-Score: Harmonic mean of precision and recall""",

        """Data Science Workflow Process

Step-by-Step Data Science Methodology:

Phase 1: Problem Definition
1. Identify business objectives
2. Define success metrics
3. Determine data requirements
4. Assess feasibility

Phase 2: Data Collection and Preparation
1. Data gathering from multiple sources
2. Data cleaning and preprocessing
3. Exploratory data analysis (EDA)
4. Feature engineering and selection

Phase 3: Model Development
1. Choose appropriate algorithms
2. Split data into train/validation/test sets
3. Train models with cross-validation
4. Hyperparameter tuning

Phase 4: Model Evaluation
1. Performance assessment using metrics
2. Model interpretation and explainability
3. Bias and fairness analysis
4. Robustness testing

Phase 5: Deployment and Monitoring
1. Model deployment to production
2. Performance monitoring
3. Model maintenance and updates
4. Feedback loop integration""",

        """AI Research Categories and Taxonomy

Artificial Intelligence Research Domains:

I. Core AI Technologies
   A. Machine Learning
      1. Supervised Learning
         a) Classification
         b) Regression
      2. Unsupervised Learning
         a) Clustering
         b) Dimensionality Reduction
      3. Reinforcement Learning
         a) Model-based methods
         b) Model-free methods

   B. Knowledge Representation
      1. Symbolic AI
      2. Knowledge Graphs
      3. Ontologies

II. Application Domains
   A. Computer Vision
      1. Image Recognition
      2. Object Detection
      3. Image Synthesis

   B. Natural Language Processing
      1. Language Understanding
      2. Language Generation
      3. Machine Translation

   C. Robotics
      1. Autonomous Navigation
      2. Manipulation
      3. Human-Robot Interaction

III. Emerging Areas
   A. Explainable AI (XAI)
   B. Federated Learning
   C. Quantum Machine Learning
   D. Neuromorphic Computing""",

        """Relationships in AI Systems

AI Component Relationships:

Data → Preprocessing → Feature Engineering → Model Training → Evaluation → Deployment

Key Relationships:
- Data Quality affects Model Performance
- Algorithm Choice influences Training Time
- Feature Engineering impacts Accuracy
- Model Complexity relates to Overfitting Risk
- Training Data Size correlates with Generalization
- Computational Resources limit Model Complexity

Research Collaborations:
- Universities partner with Tech Companies
- Open Source Communities contribute to Libraries
- Industry shares Datasets with Academia
- Government Agencies fund Research Projects

Technology Dependencies:
- Machine Learning builds on Statistics
- Deep Learning extends Neural Networks
- NLP combines Linguistics and ML
- Computer Vision uses Image Processing
- Robotics integrates Control Theory and AI"""
    ]


async def main():
    """Main function demonstrating StructRAG capabilities."""
    print("🚀 StructRAG Example - Boosting Knowledge Intensive Reasoning")
    print("=" * 70)
    
    try:
        # Initialize components
        print("🔧 Initializing components...")
        
        # Setup LLM adapter (you'll need a Gemini API key)
        llm = GeminiLLMAdapter(
            api_key=os.getenv("GEMINI_API_KEY"),
            model_name="gemini-2.5-flash"
        )
        
        # Setup tracing
        tracer = InMemoryTracingAdapter()
        
        # Initialize StructRAG adapter
        structrag_adapter = StructRAGAdapter(
            llm_adapter=llm,
            tracer=tracer,
            storage_path="./structrag_demo_storage"
        )
        
        print("✅ Components initialized successfully")
        
        # Create sample documents
        print("\n📄 Creating sample documents...")
        documents = create_sample_documents()
        print(f"✅ Created {len(documents)} sample documents")
        
        # Demonstrate indexing
        print("\n📚 Indexing documents with StructRAG...")
        indexing_use_case = IndexDocumentsWithStructRAGUseCase(llm=llm, tracer=tracer)
        
        index_result = indexing_use_case.execute(
            documents=documents,
            tenant_id="demo_tenant",
            kg_id="ai_knowledge_base",
            metadata={"domain": "artificial_intelligence", "source": "demo"}
        )
        
        print(f"✅ Indexed {index_result['document_count']} documents")
        print(f"📊 Created {index_result['chunks_created']} chunks")
        
        # Demonstrate different types of queries
        print("\n🔍 Testing StructRAG with different query types...")
        
        queries = [
            {
                "query": "What are the main types of machine learning and their applications?",
                "expected_structure": "catalogue",
                "description": "Categorical query (should use catalogue structure)"
            },
            {
                "query": "How does the data science workflow process work step by step?",
                "expected_structure": "algorithm", 
                "description": "Process query (should use algorithm structure)"
            },
            {
                "query": "What are the relationships between AI components and research collaborations?",
                "expected_structure": "graph",
                "description": "Relationship query (should use graph structure)"
            },
            {
                "query": "Compare the performance metrics for different neural network types",
                "expected_structure": "table",
                "description": "Comparison query (should use table structure)"
            },
            {
                "query": "Tell me about machine learning fundamentals",
                "expected_structure": "chunk",
                "description": "General query (should use chunk structure)"
            }
        ]
        
        query_use_case = QueryWithStructRAGUseCase(llm=llm, tracer=tracer)
        
        for i, query_info in enumerate(queries, 1):
            print(f"\n--- Query {i}: {query_info['description']} ---")
            print(f"Query: {query_info['query']}")
            print(f"Expected structure: {query_info['expected_structure']}")
            
            try:
                result = query_use_case.execute(
                    query=query_info['query'],
                    documents=documents,
                    tenant_id="demo_tenant",
                    kg_id="ai_knowledge_base",
                    return_metadata=True
                )
                
                print(f"✅ Chosen structure: {result['structure_type']}")
                print(f"📝 Subqueries: {len(result['subqueries'])}")
                print(f"💡 Answer: {result['answer'][:200]}...")
                
                # Check if structure matches expectation
                if result['structure_type'] == query_info['expected_structure']:
                    print("🎯 Structure selection: CORRECT")
                else:
                    print(f"⚠️  Structure selection: Expected {query_info['expected_structure']}, got {result['structure_type']}")
                
            except Exception as e:
                print(f"❌ Query failed: {str(e)}")
        
        # Demonstrate forced structure type
        print(f"\n🎛️ Testing forced structure type...")
        
        forced_result = query_use_case.execute(
            query="What are the main types of machine learning?",
            documents=documents,
            tenant_id="demo_tenant", 
            kg_id="ai_knowledge_base",
            structure_type="graph",  # Force graph structure
            return_metadata=True
        )
        
        print(f"✅ Forced structure type: {forced_result['structure_type']}")
        print(f"💡 Answer: {forced_result['answer'][:200]}...")
        
        # Show tracing information
        print(f"\n📊 Tracing Information:")
        metrics = tracer.get_metrics()
        for metric in metrics[-5:]:  # Show last 5 metrics
            print(f"   {metric['name']}: {metric['value']} ({metric.get('tenant_id', 'N/A')})")
        
        # Test adapter interface
        print(f"\n🔌 Testing StructRAG adapter interface...")
        
        # Test indexing via adapter
        triples = structrag_adapter.index(
            docs=documents[:2],  # Index subset
            kg_id="adapter_test",
            tenant_id="demo_tenant"
        )
        print(f"✅ Adapter indexing: {len(triples)} triples (expected 0 for StructRAG)")
        
        # Test querying via adapter
        adapter_answer = structrag_adapter.run(
            question="What are neural network types?",
            kg_id="ai_knowledge_base",
            tenant_id="demo_tenant",
            opts={"return_metadata": False}
        )
        print(f"✅ Adapter query: {adapter_answer[:100]}...")
        
        # Test translation via adapter
        query_desc, explanation = structrag_adapter.translate(
            natural_language="How does machine learning work?",
            kg_id="ai_knowledge_base", 
            tenant_id="demo_tenant"
        )
        print(f"✅ Adapter translation: {query_desc}")
        print(f"   Explanation: {explanation}")
        
        # Get adapter status
        status = structrag_adapter.get_status()
        print(f"✅ Adapter status: {status['adapter_type']}")
        print(f"   Storage: {status['storage_path']}")
        print(f"   Knowledge bases: {status['knowledge_bases']}")
        
    except Exception as e:
        print(f"❌ Example failed: {str(e)}")
        logger.error(f"StructRAG example failed: {str(e)}", exc_info=True)
    
    print(f"\n🎉 StructRAG example completed!")
    print("📝 Key Features Demonstrated:")
    print("   ✓ Multi-agent framework (Analysis, Construction, Retrieval, Merging)")
    print("   ✓ Automatic structure type selection")
    print("   ✓ Hybrid knowledge structurization")
    print("   ✓ Knowledge-intensive reasoning")
    print("   ✓ GraphRetrieverPort compatibility")


if __name__ == "__main__":
    asyncio.run(main())
