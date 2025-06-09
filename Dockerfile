# Build stage
FROM python:3.11-slim AS builder
WORKDIR /app
COPY pyproject.toml README.md CHANGELOG.md ./
COPY src ./src
RUN pip install --upgrade pip && \
    pip wheel --no-deps --wheel-dir /wheels .

# Runtime stage
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for asyncpg
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md CHANGELOG.md ./
COPY --from=builder /wheels /tmp/wheels

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser && \
    pip install --upgrade pip && \
    pip install --no-cache-dir /tmp/wheels/*.whl && \
    rm -rf /tmp/wheels /root/.cache/pip

COPY src ./src
COPY README.md CHANGELOG.md ./

USER appuser

CMD ["python", "-m", "xyte_mcp.http"]
