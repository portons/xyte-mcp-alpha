### Quick compliance check vs. current MCP best-practice list

| Area                         | Status                                                                                                                            | Highlights / Deviations |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| **SDK & transport**          | ✅ Uses `mcp.server.fastmcp`; stdio entry point. No HTTP endpoint or stream-able mode yet.                                         |                         |
| **Tools vs Resources split** | ✅ Largely correct.                                                                                                                |                         |
| **Type safety & schema**     | ⚠️ Inputs typed (Pydantic) **but outputs are returned as raw `str` or un-validated `dict`**, so the LLM sees un-structured blobs. |                         |
| **Error handling**           | ⚠️ Catches `Exception` and returns string/dict; should raise `MCPError` with code & message.                                      |                         |
| **Async & reuse**            | ✅ Async HTTPX client; but **single global client w/out retry / back-off / pool-reuse settings**.                                  |                         |
| **Logging & metrics**        | ⚠️ Only root-level `logging.basicConfig`. No structured logs, no Prometheus counters.                                             |                         |
| **Security**                 | ⚠️ Relies solely on `XYTE_API_KEY` env-var. No option for per-user tokens, no secrets-manager integration.                        |                         |
| **Tests / CI**               | ❌ No tests, no linting, no workflow.                                                                                              |                         |
| **Packaging & versioning**   | ✅ PEP 621 metadata. Version pinned at 0.1.0; spec.md accidentally committed (should live in docs).                                |                         |
| **Deployment**               | ⚠️ No Dockerfile, no K8s manifests, no health-check route; stdio-only entry point unsuitable for remote hosting.                  |                         |
| **Docs**                     | ✅ README good, but no auto-generated tool docs, no OpenAPI artefact for MCP itself.                                               |                         |



---

## Task plan to turn it into a “best-in-class” MCP server

> **Legend:**
> `[P0]` = must-do before 1.0 release
> `[P1]` = high value, next sprint
> `[P2]` = nice-to-have / backlog

---

### 1. Protocol-level improvements

1. **Add HTTP + streaming transport** `[P0]`

    * Expose `app = mcp.asgi_app()` and launch with Uvicorn (entry: `python -m xyte_mcp_alpha.http`).
    * Support new single-endpoint streaming (`/mcp`) plus legacy `/invoke` + `/sse` fallback.
2. **Upgrade error model** `[P0]`

    * Replace ad-hoc `{'error': …}` returns with `from mcp.server.errors import MCPError` and raise `MCPError(code="xyte_api_error", message=str(e))`.
    * Map XYTE 4xx/5xx to meaningful MCP error codes.
3. **Structured outputs** `[P0]`

    * Return `dict`/Pydantic models; never raw `str`.
    * Example: `class Device(BaseModel): id:str name:str …` and `List[Device]` for `get_devices`.
4. **Schema validation on inputs** `[P1]`

    * Wrap primitive args (e.g. `device_id:str`) into small Pydantic models and annotate tools with `Annotated` to auto-generate richer JSON-Schema for LLM.

### 2. Code-quality & maintainability

1. **Refactor into feature modules** `[P1]`

    * `resources.py`, `tools.py`, `models.py`, `client.py`, `server.py` thin bootstrap.
2. **Use dependency-injection for API client** `[P1]`

    * Replace global `api_client` with `@mcp.server.on_request` context that yields a client instance (makes testing easier).
3. **Remove dead files** `[P0]`

    * `spec.md` is generated; move to `docs/` or delete.

### 3. Reliability & performance

1. **HTTPX client tweaks** `[P0]`

    * Enable `limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)` and `retries = 3` with exponential back-off.
2. **Caching layer** `[P1]`

    * Optional in-memory or Redis cache for `get_devices`, `get_incidents`, etc., with TTL env-configurable.
3. **Timeout & cancel support** `[P0]`

    * Respect `context.deadline` from MCP request; cancel underlying HTTPX call if exceeded.
4. **Prometheus metrics** `[P1]`

    * Expose `/metrics` endpoint (if HTTP mode). Track per-tool latency, XYTE API status codes, error counts.

### 4. Security & configuration

1. **Secret management** `[P0]`

    * Support `.env`, but document vault/K8s-secret injection.
2. **Per-user tokens option** `[P2]`

    * Allow clients to pass `api_key` as part of initialization handshake; store in in-memory map keyed by session ID.

### 5. Testing & CI

1. **Unit tests** `[P0]`

    * 100 % tool/resource happy-path coverage with `pytest` + `pytest-asyncio`.
2. **Integration tests** `[P1]`

    * Spin up a mock XYTE API with `respx` to validate end-to-end MCP calls.
3. **Static analysis** `[P0]`

    * Add `ruff`, `mypy --strict`, `pre-commit`.
4. **GitHub Actions** `[P0]`

    * Matrix on 3.9 – 3.12, run unit tests + linting, build Docker image on tag.

### 6. Deployment artefacts

1. **Dockerfile** `[P0]`

   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   COPY . .
   RUN pip install --no-cache-dir .
   ENV PYTHONUNBUFFERED=1
   CMD ["uvicorn", "xyte_mcp_alpha.http:app", "--host", "0.0.0.0", "--port", "8080"]
   ```
2. **K8s manifests / Helm chart** `[P1]`

    * Deployment, Service, HPA, secret mount for `XYTE_API_KEY`, ConfigMap for optional base URL.
3. **Health & readiness probes** `[P0]`

    * `/healthz` returns 200 and `list_tools` check.

### 7. Documentation

1. **Auto-generate MCP capability JSON** `[P1]`

    * `poetry run mcp introspect` → publish in `docs/capabilities.json`.
2. **Swagger-style docs for XYTE wrappers** `[P2]`

    * Create Markdown tables describing tools/resources, parameters, examples.
3. **Replace README usage examples with runnable `mcp dev` GIF** `[P2]`.

### 8. Versioning & release

1. **Semantic version bump to `1.0.0` once P0 tasks done** `[P0]`.
2. **CHANGELOG.md** with autogenerated release notes using `git-cliff`.

### 9. Community & contribution

1. **Contributing guide + code-of-conduct** `[P2]`.
2. **Publish to PyPI with wheels + sdist** `[P1]`.
3. **Submit to `awesome-mcp-servers` index** `[P2]`.

---

### Immediate next sprint (P0 items only)

| Epic               | Tasks             |
| ------------------ | ----------------- |
| Protocol hardening | 1.1, 1.2, 1.3     |
| Reliability        | 3.1, 3.3          |
| Security/config    | 4.1               |
| Testing/CI         | 5.1, 5.3, 5.4     |
| Deployment         | 6.1, 6.3          |
| House-cleaning     | 2.3, 3.bulk fixes |

Total ≈ **20 - 25 hours** for a senior dev; after merge, cut `v1.0.0`.
