# Use official Python image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install UV using pip as fallback for network issues
RUN pip install uv

# Set UV environment variables
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Set Jenkins MCP environment variables
ENV JENKINS_MCP_CONFIG_FILE=/app/config.yaml
ENV JENKINS_MCP_SCENARIOS_FILE=/app/scenarios.yaml
ENV JENKINS_MCP_LOG_LEVEL=INFO

# Add health check labels
LABEL maintainer="xhuaustc@gmail.com"
LABEL description="Jenkins MCP - Model Context Protocol server for Jenkins automation"
LABEL version="1.0.0"

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/
COPY scenarios.default.yaml ./scenarios.default.yaml

# Use UV to create virtual environment and install project
RUN uv venv && \
    uv pip install -e .

# Set PATH to use UV virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Expose port (modify if needed)
EXPOSE 8000

# Default startup command (use UV to run, default stdio mode)
# Can be overridden by environment variable or command line argument:
# docker run jenkins-mcp --transport sse
# docker run jenkins-mcp --transport http --port 8080
CMD ["uv", "run", "jenkins"]