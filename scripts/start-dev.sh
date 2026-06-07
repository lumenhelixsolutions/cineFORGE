#!/bin/bash
set -e

echo "=== CineForge Development Start ==="

# Check Python
if ! command -v python3.12 &> /dev/null; then
    echo "ERROR: Python 3.12 required"
    exit 1
fi

# Check Node
if ! command -v npm &> /dev/null; then
    echo "ERROR: npm required"
    exit 1
fi

# Check Rust / Cargo
if ! command -v cargo &> /dev/null; then
    echo "WARNING: Rust not found. Tauri builds will fail."
fi

# Setup venv if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3.12 -m venv .venv
fi

# Install backend deps
source .venv/bin/activate
pip install -e ".[vertex,fal,dev]"

# Install frontend deps
if [ ! -d "ui/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd ui && npm install && cd ..
fi

# Start backend in background
echo "Starting FastAPI backend on port 8765..."
python -m backend.app &
BACKEND_PID=$!

# Wait for backend
for i in {1..30}; do
    if curl -s http://127.0.0.1:8765/health > /dev/null; then
        echo "Backend ready."
        break
    fi
    sleep 1
done

# Start frontend dev server
echo "Starting Vite dev server..."
cd ui && npm run dev

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
