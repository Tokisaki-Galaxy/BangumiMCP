# Use a Python base image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a multi-stage build
ENV UV_LINK_MODE=copy

# Install the project's dependencies from the lockfile and pyproject.toml
WORKDIR /app
COPY uv.lock pyproject.toml /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Final stage
FROM python:3.12-slim-bookworm

# Create a non-privileged user
RUN useradd -m -u 1000 bangumi

WORKDIR /app

# Copy the environment and source code, setting ownership to bangumi
COPY --from=builder --chown=bangumi:bangumi /app /app

# Place executables in the path
ENV PATH="/app/.venv/bin:$PATH"

# Switch to the non-privileged user
USER bangumi

# Run the MCP server on stdio
ENTRYPOINT ["python", "main.py"]
