# noema-agent Dockerfile
# Multi-stage build: minimal production image + isolated dev/test layer
#
# Stages:
#   builder  — installs all deps into a venv (prod + dev)
#   prod     — copies venv + app only; no test deps, no build tools
#   dev      — extends prod with test deps; used for local dev and CI
#
# Usage:
#   Production:  docker build --target prod -t noema-agent:prod .
#   Dev/test:    docker build --target dev  -t noema-agent:dev  .
#   Default:     docker build -t noema-agent . (builds prod)

# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install pip + venv tooling only
RUN pip install --no-cache-dir --upgrade pip

# Copy dependency manifests first for layer caching
COPY requirements.txt requirements-dev.txt ./

# Create venv and install prod deps
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt


# ── Stage 2: prod ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS prod

# Non-root user for minimal attack surface
RUN addgroup --system noema && adduser --system --ingroup noema noema

WORKDIR /app

# Copy venv from builder (no build tools, no pip)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source only
COPY app/ ./app/

# Drop to non-root
USER noema

# Health check: lightweight GET /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]


# ── Stage 3: dev ──────────────────────────────────────────────────────────────
FROM prod AS dev

# Switch back to root to install dev deps
USER root

COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy test files
COPY tests/ ./tests/
COPY test_api.py test_compliance.py ./

# Back to non-root for runtime
USER noema

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
