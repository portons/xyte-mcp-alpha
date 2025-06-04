FROM python:3.11-slim
WORKDIR /app
COPY requirements/prod.txt .
RUN pip install --no-cache-dir -r prod.txt
COPY src ./src
RUN useradd -m mcp
USER mcp
EXPOSE 8000
HEALTHCHECK CMD curl -f http://localhost:8000/healthz || exit 1
CMD ["uvicorn", "xyte_mcp.server:app", "--host", "0.0.0.0", "--port", "8000"]
