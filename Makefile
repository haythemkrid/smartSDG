# SmartSDG Core Engine Makefile
# Commands from AGENTS.md

.PHONY: setup test lint run-pipeline deploy-module up help

# Default target
help:
	@echo "SmartSDG Core Engine - Available commands:"
	@echo "  make setup           # Create venv and install dependencies"
	@echo "  make test            # Run offline pytest"
	@echo "  make lint            # Run ruff linter"
	@echo "  make run-pipeline    # Run DVC pipeline for a module (not implemented yet)"
	@echo "  make deploy-module   # Deploy a module (not implemented yet)"
	@echo "  make up              # Start Docker Compose stack (not implemented yet)"

# Create virtual environment and install dependencies
setup:
	@echo "Creating virtual environment..."
	python3.13 -m venv .venv 2>/dev/null || python3.12 -m venv .venv 2>/dev/null || python3.11 -m venv .venv 2>/dev/null || python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"
	@echo "Setup complete. Activate with: source .venv/bin/activate"

# Run tests (offline only)
test:
	@echo "Running tests..."
	.venv/bin/pytest tests/ -v

# Run linter
lint:
	@echo "Running linter..."
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .

# Run pipeline for a module
run-pipeline:
	@echo "Error: run-pipeline not implemented yet"
	@exit 1

# Deploy a module
deploy-module:
	@echo "Error: deploy-module not implemented yet"
	@exit 1

# Start Docker Compose stack
up:
	@echo "Error: up not implemented yet"
	@exit 1