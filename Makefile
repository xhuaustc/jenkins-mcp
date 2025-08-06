# Set the Python version from cookiecutter or default to 3.11
PYTHON_VERSION := "3.11"

.PHONY: setup run dev test clean fmt type-check

.PHONY: setup
# Setup with uv
setup:
	# Check if uv is installed, install if not
	@which uv >/dev/null || pip install uv
	# Create a virtual environment
	uv venv
	# Install dependencies with development extras
	uv pip install -e ".[dev]"
	@echo "✅ Environment setup complete. Activate it with 'source .venv/bin/activate' (Unix/macOS) or '.venv\\Scripts\activate' (Windows)"

.PHONY: run
# Run the server directly
run:
	uv run -m jenkins

.PHONY: dev
# Run in development mode with MCP inspector
dev:
	uv run mcp dev src/jenkins/__main__.py

.PHONY: test
# Run tests
test:
	uv run pytest

.PHONY: fmt
# Format code with ruff
fmt:
	uv run ruff format jenkins
	uv run ruff check --fix jenkins

.PHONY: type-check
# Check types with mypy
type-check:
	mypy jenkins

.PHONY: clean
# Clean up build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
