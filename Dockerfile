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

# Create non-root user
RUN useradd -m appuser

# Install application wheel only
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

COPY src ./src
COPY README.md CHANGELOG.md ./

USER appuser

CMD ["serve"]
