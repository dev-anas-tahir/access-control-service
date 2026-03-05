FROM python:3.12-slim

# Copy uv binary from official image — don't install via pip
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy lockfile and project metadata first (layer caching)
COPY pyproject.toml uv.lock ./

# Install deps only — not the project itself (faster rebuilds)
RUN uv sync --frozen --no-cache --no-install-project

# Now copy source
COPY . .

# Final sync including project
RUN uv sync --frozen --no-cache

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
