#!/bin/bash
# UV Project Management Script for Samvaad Sathi Backend

echo "🚀 Samvaad Sathi Backend - UV Project Management"
echo "================================================"

case "$1" in
    "install")
        echo "📦 Installing dependencies..."
        uv sync --extra dev
        ;;
    "run")
        echo "🏃 Running: $2"
        uv run "$2"
        ;;
    "lint")
        echo "🔍 Running linting tools..."
        echo "Running Black (code formatting)..."
        uv run black backend/backend/src/
        echo "Running isort (import sorting)..."
        uv run isort backend/backend/src/
        echo "Running MyPy (type checking)..."
        uv run mypy backend/backend/src/
        ;;
    "test")
        echo "🧪 Running tests..."
        uv run pytest backend/backend/tests/
        ;;
    "dev")
        echo "🛠️ Starting development server..."
        uv run uvicorn backend.backend.src.main:app --reload --host 0.0.0.0 --port 8000
        ;;
    *)
        echo "Usage: $0 {install|run|lint|test|dev}"
        echo ""
        echo "Commands:"
        echo "  install  - Install all dependencies (including dev)"
        echo "  run      - Run a command in the uv environment"
        echo "  lint     - Run all linting tools (black, isort, mypy)"
        echo "  test     - Run tests with pytest"
        echo "  dev      - Start the development server"
        echo ""
        echo "Examples:"
        echo "  $0 install"
        echo "  $0 run python --version"
        echo "  $0 lint"
        echo "  $0 test"
        echo "  $0 dev"
        ;;
esac
