
#!/bin/bash
# Setup script for Hugging Face Transformers HTTP Server

echo "🚀 Setting up Hugging Face Transformers HTTP Server"
echo "=================================================="

# Check if transformers is installed
if ! python -c "import transformers" &> /dev/null; then
    echo "📦 Installing transformers..."
    pip install transformers[serve] torch torchvision torchaudio
else
    echo "✅ Transformers already installed"
fi

# Check if accelerate is installed (for better performance)
if ! python -c "import accelerate" &> /dev/null; then
    echo "📦 Installing accelerate for better performance..."
    pip install accelerate
fi

# Function to start transformers server
start_server() {
    local model_name=${1:-"microsoft/DialoGPT-medium"}
    local port=${2:-8001}
    local host=${3:-"0.0.0.0"}
    
    echo "🚀 Starting transformers server..."
    echo "   Model: $model_name"
    echo "   Host: $host"
    echo "   Port: $port"
    echo ""
    
    # Start the server
    transformers serve \
        --model "$model_name" \
        --host "$host" \
        --port "$port" \
        --workers 1 \
        --timeout 120 \
        --api-version v1 \
        --enable-cors &
    
    SERVER_PID=$!
    echo "📝 Server PID: $SERVER_PID"
    
    # Wait a bit for server to start
    sleep 5
    
    # Test the server
    echo "🧪 Testing server health..."
    if curl -s "http://$host:$port/v1/models" > /dev/null; then
        echo "✅ Transformers server is healthy!"
        echo ""
        echo "🔗 Server endpoints:"
        echo "   - Models: http://$host:$port/v1/models"
        echo "   - Chat: http://$host:$port/v1/chat/completions"
        echo "   - Embeddings: http://$host:$port/v1/embeddings"
        echo ""
        echo "🎯 Environment variables to set:"
        echo "export TRANSFORMERS_SERVER_URL=http://$host:$port"
        echo "export TRANSFORMERS_MODEL_NAME=$model_name"
        echo "export USE_LOCAL_TRANSFORMERS=true"
    else
        echo "❌ Server health check failed"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
}

# Function to stop transformers server
stop_server() {
    echo "🛑 Stopping transformers server..."
    pkill -f "transformers serve"
    echo "✅ Server stopped"
}

# Function to list available models
list_models() {
    echo "📋 Popular models for GraphRAG:"
    echo ""
    echo "🧠 Text Generation Models:"
    echo "   - microsoft/DialoGPT-medium (default, good for conversation)"
    echo "   - microsoft/DialoGPT-large (larger, better quality)"
    echo "   - facebook/blenderbot-400M-distill (lightweight, good for chat)"
    echo "   - google/flan-t5-base (instruction-following)"
    echo "   - google/flan-t5-large (larger instruction model)"
    echo ""
    echo "🔍 Embedding Models:"
    echo "   - sentence-transformers/all-MiniLM-L6-v2 (default, fast)"
    echo "   - sentence-transformers/all-mpnet-base-v2 (better quality)"
    echo "   - sentence-transformers/multi-qa-MiniLM-L6-cos-v1 (QA optimized)"
    echo ""
    echo "🛠️ Specialized Models:"
    echo "   - facebook/bart-large-cnn (summarization)"
    echo "   - deepset/roberta-base-squad2 (question answering)"
    echo "   - microsoft/codebert-base (code understanding)"
    echo ""
}

# Function to install specific model
install_model() {
    local model_name=$1
    if [ -z "$model_name" ]; then
        echo "❌ Please provide a model name"
        echo "Usage: $0 install <model_name>"
        exit 1
    fi
    
    echo "📥 Installing model: $model_name"
    python -c "
from transformers import AutoTokenizer, AutoModel
try:
    print('Downloading tokenizer...')
    AutoTokenizer.from_pretrained('$model_name')
    print('Downloading model...')
    AutoModel.from_pretrained('$model_name')
    print('✅ Model $model_name installed successfully!')
except Exception as e:
    print(f'❌ Failed to install model: {e}')
    exit(1)
"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start [model] [port] [host]  Start transformers server (default: DialoGPT-medium, 8001, 0.0.0.0)"
    echo "  stop                         Stop transformers server"
    echo "  install <model>              Pre-download a model"
    echo "  list                         List popular models for GraphRAG"
    echo "  test                         Test server connectivity"
    echo ""
    echo "Examples:"
    echo "  $0 start                                    # Start with defaults"
    echo "  $0 start google/flan-t5-base 8002          # Start with specific model and port"
    echo "  $0 install microsoft/DialoGPT-large        # Pre-download a model"
    echo "  $0 list                                     # Show available models"
}

# Function to test server
test_server() {
    local server_url=${1:-"http://0.0.0.0:8001"}
    
    echo "🧪 Testing transformers server at $server_url"
    echo ""
    
    # Test models endpoint
    echo "📋 Testing models endpoint..."
    curl -s "$server_url/v1/models" | python -m json.tool
    echo ""
    
    # Test chat completions
    echo "💬 Testing chat completions..."
    curl -s -X POST "$server_url/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d '{
            "model": "microsoft/DialoGPT-medium",
            "messages": [{"role": "user", "content": "Hello! How are you?"}],
            "max_tokens": 50,
            "temperature": 0.7
        }' | python -m json.tool
    echo ""
}

# Main script logic
case "${1:-start}" in
    "start")
        start_server "$2" "$3" "$4"
        ;;
    "stop")
        stop_server
        ;;
    "install")
        install_model "$2"
        ;;
    "list")
        list_models
        ;;
    "test")
        test_server "$2"
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        echo "❌ Unknown command: $1"
        show_usage
        exit 1
        ;;
esac
