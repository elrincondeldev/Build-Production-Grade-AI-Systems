# syntax=docker/dockerfile:1
# Multi-stage build (📖 lesson 1.5):
#   stage 1 "builder" has the build tools and resolves dependencies with uv
#   stage 2 "runtime" contains only the virtualenv, the model artifact and a non-root user
# Result: a smaller image with fewer packages that could contain vulnerabilities.

############################
# Stage 1: build
############################
FROM python:3.12-slim AS builder

# Pin the uv version so builds are reproducible.
COPY --from=ghcr.io/astral-sh/uv:0.8.0 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# 1) Dependencies first: this layer is cached until pyproject.toml/uv.lock change,
#    so editing your code does not re-download every package.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# 2) Then the project itself (changes often, cheap to rebuild).
COPY README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

############################
# Stage 2: runtime
############################
FROM python:3.12-slim AS runtime

# Run as an unprivileged user: if the app is compromised, the attacker is not root.
RUN groupadd --system --gid 10001 app && \
    useradd --system --uid 10001 --gid app --no-create-home app

WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Bake ONE verified model version into the image (image tag == code + model).
# The alternative, downloading from a model registry at startup, is discussed in lesson 1.5.
COPY --chown=app:app artifacts/fraud-model/ /app/artifacts/fraud-model/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    KESTREL_MODEL_DIR=/app/artifacts/fraud-model \
    KESTREL_MODEL_VERSION=latest \
    KESTREL_ENVIRONMENT=prod

USER app
EXPOSE 8001

# Docker-level liveness check. Kubernetes ignores this and uses its own probes (k8s/deployment.yaml).
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=2)"

# Exec form (JSON array) so uvicorn is PID 1 and receives SIGTERM for graceful shutdown.
CMD ["uvicorn", "kestrel_fraud.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8001"]
