
#!/bin/bash
# Setup script for FalkorDB with GraphRAG SDK

echo "🔧 Setting up FalkorDB for GraphRAG SDK"
echo "======================================"

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "✅ Docker found"
    
    # Check if FalkorDB container is running
    if docker ps | grep -q falkordb; then
        echo "✅ FalkorDB container is already running"
    else
        echo "🚀 Starting FalkorDB container..."
        
        # Create data directory
        mkdir -p ./data
        
        # Start FalkorDB container
        docker run -d \
            --name falkordb-graphrag \
            -p 6379:6379 \
            -p 3000:3000 \
            -v ./data:/data \
            falkordb/falkordb:latest
        
        echo "✅ FalkorDB container started"
        echo "   - Redis port: 6379"
        echo "   - Browser UI: http://localhost:3000"
    fi
    
    echo ""
    echo "🔑 Environment Variables to Set:"
    echo "FALKORDB_HOST=localhost"
    echo "FALKORDB_PORT=6379"
    echo "FALKORDB_USER=(optional)"
    echo "FALKORDB_PASSWORD=(optional)"
    echo "GEMINI_API_KEY=your_gemini_api_key"
    
else
    echo "❌ Docker not found. Please install Docker first."
    echo ""
    echo "Alternative: Install FalkorDB locally"
    echo "See: https://docs.falkordb.com/installation.html"
fi

echo ""
echo "📦 Installing GraphRAG SDK..."
pip install graphrag_sdk

echo ""
echo "🎉 Setup complete! You can now use GraphRAG SDK with FalkorDB."
echo ""
echo "💡 Next steps:"
echo "1. Set environment variables above"
echo "2. Run: python examples/graphrag_sdk_example.py"
echo "3. Integrate with your agents and workflows"
