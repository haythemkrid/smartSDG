# SmartSDG Core Engine Makefile
# Commands from AGENTS.md

.PHONY: setup test lint run-pipeline deploy-module up restore-demo snapshot-demo help

# Default target
help:
	@echo "SmartSDG Core Engine - Available commands:"
	@echo "  make setup           # Create venv and install dependencies"
	@echo "  make test            # Run offline pytest"
	@echo "  make lint            # Run ruff linter"
	@echo "  make run-pipeline    # Run DVC pipeline for a module (MODULE=hydrowatch)"
	@echo "  make deploy-module   # Deploy a module (MODULE=hydrowatch)"
	@echo "  make up              # Start Docker Compose stack (API, MLflow, frontend, orchestrator)"

# Create virtual environment and install dependencies
setup:
	@echo "Creating virtual environment..."
	python3.11 -m venv .venv 2>/dev/null || python3.12 -m venv .venv 2>/dev/null || python3.10 -m venv .venv 2>/dev/null || python3 -m venv .venv
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
	@if [ -z "$(MODULE)" ]; then echo "Error: MODULE not specified. Usage: make run-pipeline MODULE=hydrowatch"; exit 1; fi
	@echo "Running DVC pipeline for module: $(MODULE)..."
	.venv/bin/python -m core.registry.run_pipeline $(MODULE)

# Deploy a module
deploy-module:
	@if [ -z "$(MODULE)" ]; then echo "Error: MODULE not specified. Usage: make deploy-module MODULE=hydrowatch"; exit 1; fi
	@echo "Deploying module: $(MODULE)..."
	.venv/bin/python -c "from core.registry.module_loader import ModuleLoader; loader = ModuleLoader(); loader.deploy_module('$(MODULE)'); print('Module $(MODULE) deployed successfully')"

# Start Docker Compose stack
up:
	@echo "Starting Docker Compose stack..."
	docker compose up -d
	@echo "Services started. API: http://localhost:8000, MLflow: http://localhost:5000, Frontend: http://localhost:8501"

# Restore demo data from demo_data/ to data/outputs/
restore-demo:
	@echo "Restoring demo data..."
	rm -rf data/outputs
	cp -r demo_data data/outputs
	@echo "Demo data restored."

# Snapshot current data/outputs/ to demo_data/
snapshot-demo:
	@echo "Snapshotting demo data..."
	rm -rf demo_data
	cp -r data/outputs demo_data
	@echo "Demo data snapshotted."