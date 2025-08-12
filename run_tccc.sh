#!/bin/bash
# TCCC RAG System Launcher for HPC Environments
# 
# Usage: ./run_tccc.sh [query] [--urgent]
# Examples:
#   ./run_tccc.sh "massive hemorrhage control"
#   ./run_tccc.sh "airway obstruction" --urgent
#   ./run_tccc.sh  # Interactive mode

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/tccc_env"
OLLAMA_DIR="$SCRIPT_DIR"

echo "🏥 Starting TCCC Emergency Medical Reference System"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Python virtual environment not found at $VENV_DIR"
    echo "Run setup first or check installation"
    exit 1
fi

# Check if Ollama server is running
if ! pgrep -f "ollama serve" > /dev/null; then
    echo "⚠️  Ollama server not running. Starting server..."
    cd "$OLLAMA_DIR"
    export PATH="$PWD/bin:$PATH"
    export LD_LIBRARY_PATH="$PWD/lib/ollama:$LD_LIBRARY_PATH"
    
    # Start Ollama server in background
    nohup ./bin/ollama serve > ollama.log 2>&1 &
    OLLAMA_PID=$!
    echo "🔄 Ollama server starting (PID: $OLLAMA_PID)..."
    
    # Wait for server to be ready
    for i in {1..30}; do
        if curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
            echo "✅ Ollama server ready"
            break
        fi
        echo "⏳ Waiting for Ollama server... ($i/30)"
        sleep 1
    done
    
    if ! curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
        echo "❌ Failed to start Ollama server"
        exit 1
    fi
else
    echo "✅ Ollama server already running"
fi

# Activate virtual environment and run TCCC system
echo "🚀 Launching TCCC system..."
source "$VENV_DIR/bin/activate"
cd "$SCRIPT_DIR"

# Pass all arguments to the Python script
python tccc_simple.py "$@"