# Stage 1: Build virtual environment with uv
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

COPY --from=ghcr.io/astral-sh/uv:0.5.29 /uv /uvx /bin/

WORKDIR /build

COPY apps/core-api/pyproject.toml apps/core-api/uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

# Stage 2: Final runtime image
FROM python:3.11-slim AS runner

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app:/app/strategy-contracts

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY apps/core-api/alembic.ini .
COPY apps/core-api/app ./app
COPY apps/core-api/scripts ./scripts
COPY packages/strategy-contracts ./strategy-contracts

RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /usr/sbin/nologin -M appuser && \
    chown -R appuser:appgroup /app
USER 10001:10001

EXPOSE 8000

CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
