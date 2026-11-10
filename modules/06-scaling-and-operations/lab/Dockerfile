# Multi-stage image for kestrel-platform (lesson 1.5 explains each choice).
# Build:  docker build -t kestrel-platform:dev .
# Run:    docker run --rm -p 8080:8080 kestrel-platform:dev

FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.8.0 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock* README.md ./
COPY src ./src
RUN uv sync --no-dev --no-editable

FROM python:3.12-slim AS runtime
RUN useradd --uid 10001 --create-home app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER 10001
EXPOSE 8080
CMD ["uvicorn", "kestrel_platform.main:app", "--host", "0.0.0.0", "--port", "8080"]
