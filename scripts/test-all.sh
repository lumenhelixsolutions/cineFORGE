#!/bin/bash
set -e

echo "=== CineForge Test Suite ==="

source .venv/bin/activate

echo "Running unit tests..."
pytest tests/unit/ -v

echo ""
echo "Running integration tests..."
pytest tests/integration/ -v

echo ""
echo "Running mypy strict..."
mypy backend/ --strict

echo ""
echo "Checking for leaky imports..."
pytest tests/unit/test_leaky_imports.py -v

echo ""
echo "All tests passed."
