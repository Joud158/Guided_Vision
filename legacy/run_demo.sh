#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a process is running on a port
port_in_use() {
    lsof -i:"$1" >/dev/null 2>&1
}

# Function to force clean environment
force_clean_environment() {
    echo "🧹 Force cleaning environment..."
    if [ -d "realtime_llm" ]; then
        echo "🗑️ Removing existing virtual environment..."
        rm -rf realtime_llm
    fi
    
    # Clean any Python cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    echo "✅ Environment cleaned successfully!"
}

# Check for force clean flag
if [ "$1" = "--clean" ] || [ "$1" = "-c" ]; then
    force_clean_environment
fi

echo "🚀 Starting LLM Camera Tracker Demo Setup..."
echo "=================================================="

# Check for Python
if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed."
    exit 1
else
    echo "✅ Python 3 found: $(python3 --version)"
fi

# Check system resources
echo "🔍 Checking system resources..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    total_ram=$(sysctl -n hw.memsize)
    total_ram_gb=$((total_ram / 1024 / 1024 / 1024))
else
    # Linux
    total_ram_gb=$(free -g | awk '/^Mem:/{print $2}')
fi

echo "💾 Available RAM: ${total_ram_gb}GB"
if [ "$total_ram_gb" -lt 4 ]; then
    echo "⚠️ Warning: Less than 4GB RAM detected. SmolVLM-500M requires at least 4GB RAM."
    exit 1
fi

# Ensure pip is available in base Python
if ! python3 -m pip --version >/dev/null 2>&1; then
    echo "❌ pip is not installed. Installing pip..."
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python3 get-pip.py --user
    rm get-pip.py
fi

# Ensure venv module is available
python3 -c "import venv" >/dev/null 2>&1 || {
    echo "❌ venv module not found. Installing venv..."
    python3 -m pip install --user virtualenv
}

# Check if virtual environment exists, create if it doesn't
VENV_EXISTS=false
if [ -d "realtime_llm" ]; then
    echo "♻️ Virtual environment 'realtime_llm' already exists..."
    VENV_EXISTS=true
else
    echo "🔨 Creating new virtual environment 'realtime_llm'..."
    python3 -m venv realtime_llm --clear
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment."
        echo "💡 Try: python3 -m pip install --user virtualenv"
        exit 1
    fi
    VENV_EXISTS=false
fi

# Always activate the virtual environment
echo "🔌 Activating virtual environment..."
source realtime_llm/bin/activate

# Verify we're in the virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Failed to activate virtual environment."
    echo "💡 Try deleting the realtime_llm folder and running again."
    exit 1
fi

echo "✅ Virtual environment active: $VIRTUAL_ENV"

# Install dependencies only if it's a newly created venv
if [ "$VENV_EXISTS" = false ]; then
    echo "📦 Installing dependencies for new virtual environment..."
    
    # Upgrade pip in virtual environment
    echo "⬆️ Upgrading pip in virtual environment..."
    python3 -m pip install --upgrade pip setuptools wheel
    
    # Install dependencies
    if [ ! -f "requirements.txt" ]; then
        echo "❌ requirements.txt file not found in current directory"
        echo "💡 Make sure you're running this script from the project root directory"
        exit 1
    fi
    
    echo "📦 Installing Python packages from requirements.txt..."
    python3 -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install some Python packages from requirements.txt"
        echo "💡 Check the error messages above and try running: pip install -r requirements.txt manually"
        exit 1
    fi
    
    # Install spaCy language model using spacy download command (more reliable)
    echo "📚 Installing spaCy language model (en_core_web_sm)..."
    python3 -m spacy download en_core_web_sm
    if [ $? -ne 0 ]; then
        echo "⚠️ spaCy model download failed, trying alternative method..."
        python3 -m pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.5.0/en_core_web_sm-3.5.0.tar.gz
    fi
    
    echo "✅ Dependencies installed successfully!"
else
    echo "⏭️ Skipping dependency installation (using existing venv)"
    echo "💡 To reinstall dependencies, run: $0 --clean"
fi

# Create output directory for graphs
echo "📁 Creating output directory..."
mkdir -p output

# Check for Homebrew and install llama.cpp
echo "🍺 Checking for Homebrew..."
if ! command_exists brew; then
    echo "❌ Homebrew is not installed. Please install Homebrew first: https://brew.sh/"
    exit 1
fi

echo "✅ Homebrew found"

# Install llama.cpp if not already installed
if ! command_exists llama-server; then
    echo "📦 Installing llama.cpp via Homebrew..."
    brew install llama.cpp
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install llama.cpp via Homebrew."
        echo "💡 Try running: brew update && brew install llama.cpp"
        exit 1
    fi
    # Verify installation worked
    if ! command_exists llama-server; then
        echo "❌ llama-server command not found after installation."
        echo "💡 Try running: which llama-server"
        exit 1
    fi
    echo "✅ llama.cpp installed successfully"
else
    echo "✅ llama-server already available"
fi

# Set model to SmolVLM-500M
VLM_MODEL="ggml-org/SmolVLM-500M-Instruct-GGUF"
echo "🤖 Using SmolVLM-500M (Fast, lightweight - 500M parameters)"

# Check for Hugging Face token
if [ -z "$HF_TOKEN" ]; then
    echo "⚠️  No Hugging Face token found. You may hit rate limits."
    echo "💡 To avoid rate limits, set your HF_TOKEN environment variable:"
    echo "   export HF_TOKEN=your_token_here"
    echo "   Or add it to your .env file"
    HF_TOKEN_ARG=""
else
    echo "✅ Using Hugging Face token"
    HF_TOKEN_ARG="--hf-token $HF_TOKEN"
fi

# Download and wait for the model (this happens automatically when llama-server starts)
echo "📥 Model will be downloaded automatically when llama-server starts..."
echo "⏳ This may take a few minutes on first run (model is ~500MB)"

# Kill any existing processes on our ports
for port in 8000 8080 8081; do
    if port_in_use "$port"; then
        echo "🔄 Freeing port $port..."
        lsof -ti:"$port" | xargs kill -9 2>/dev/null
    fi
done

# Start llama-server in the background
echo "🚀 Starting llama server with model: $VLM_MODEL"
llama-server -hf $VLM_MODEL $HF_TOKEN_ARG > llama-server.log 2>&1 &
LLAMA_PID=$!

# Wait for llama-server to start and download model if needed
echo "⏳ Waiting for llama-server to initialize and download model..."
echo "📋 You can check llama-server.log for download progress"
sleep 10

# Wait up to 60 seconds for the llama-server to be ready (model download takes time)
for i in {1..30}; do
    if port_in_use 8080; then
        break
    fi
    echo "   Still waiting for llama-server... (${i}/30)"
    sleep 2
done

# Verify llama-server is running
if ! kill -0 $LLAMA_PID 2>/dev/null; then
    echo "❌ llama-server failed to start. Check llama-server.log for details."
    exit 1
fi

# Final check if llama-server port is responding
if ! port_in_use 8080; then
    echo "❌ llama-server is not listening on port 8080 after 60 seconds. Check llama-server.log for details."
    exit 1
fi

echo "✅ llama-server is running successfully"

# Start scene graph server in the background
if [ ! -f "scene_graph_server.py" ]; then
    echo "❌ scene_graph_server.py file not found in current directory"
    echo "💡 Make sure you're running this script from the project root directory"
    exit 1
fi

if [ ! -f "realtime_llm/bin/python3" ]; then
    echo "❌ Virtual environment Python executable not found"
    echo "💡 Try running: $0 --clean"
    exit 1
fi

echo "🔄 Starting scene graph server..."
./realtime_llm/bin/python3 scene_graph_server.py > scene-graph-server.log 2>&1 &
GRAPH_PID=$!

# Wait for scene graph server to start
echo "⏳ Waiting for scene graph server to fully initialize..."
sleep 2

# Wait up to 30 seconds for the server to be ready
for i in {1..15}; do
    if port_in_use 8081; then
        break
    fi
    echo "   Still waiting for scene graph server... (${i}/15)"
    sleep 2
done

# Verify scene graph server is running
if ! kill -0 $GRAPH_PID 2>/dev/null; then
    echo "❌ scene graph server failed to start. Check scene-graph-server.log for details."
    exit 1
fi

# Final check if scene graph server port is responding
if ! port_in_use 8081; then
    echo "❌ scene graph server is not listening on port 8081 after 30 seconds. Check scene-graph-server.log for details."
    exit 1
fi

echo "✅ scene graph server is running successfully"

# Start HTTP server
echo "🌐 Starting local web server on http://localhost:8000"
python3 -m http.server 8000 > http-server.log 2>&1 &
HTTP_PID=$!

# Open the page in browser
sleep 1
echo "🌍 Opening web interface..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:8000/index.html
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open http://localhost:8000/index.html
fi

echo ""
echo "✅ All services are running:"
echo "🔹 llama-server (PID: $LLAMA_PID) - http://localhost:8080"
echo "🔹 scene-graph-server (PID: $GRAPH_PID) - http://localhost:8081"
echo "🔹 HTTP server (PID: $HTTP_PID) - http://localhost:8000"
echo ""
echo "📝 Log files:"
echo "- llama-server.log"
echo "- scene-graph-server.log"
echo "- http-server.log"
echo ""
echo "Press Ctrl+C to stop all services"

# Function to cleanup processes on exit
cleanup() {
    echo ""
    echo "🛑 Stopping all services..."
    kill $LLAMA_PID $GRAPH_PID $HTTP_PID 2>/dev/null
    deactivate 2>/dev/null
    echo "👋 Goodbye!"
    exit 0
}

# Register cleanup function to run on script termination
trap cleanup EXIT

# Wait for all background processes
wait
