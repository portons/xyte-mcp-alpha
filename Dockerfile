# Build stage
FROM python:3.13-slim AS builder
WORKDIR /app
COPY pyproject.toml README.md CHANGELOG.md ./
COPY src ./src
RUN pip install --upgrade pip && \
    pip wheel --no-deps --wheel-dir /wheels .

# Runtime stage
FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /wheels /tmp/wheels

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser && \
    pip install --no-cache-dir /tmp/wheels/*.whl && \
    rm -rf /tmp/wheels /root/.cache/pip

COPY src ./src
COPY README.md CHANGELOG.md ./

USER appuser

CMD ["python", "-m", "xyte_mcp_alpha.http"]
