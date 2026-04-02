FROM python:3.12-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency + build files first for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies (no dev deps, no editable install yet)
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY src/ src/

# Install the project itself
RUN uv sync --frozen --no-dev

# FastMCP reads these for SSE/HTTP transport
ENV MCP_TRANSPORT=sse
ENV FASTMCP_HOST=0.0.0.0

# Railway injects PORT; forward it to FastMCP's FASTMCP_PORT
CMD ["sh", "-c", "FASTMCP_PORT=${PORT:-8000} uv run rappi-mcp"]
