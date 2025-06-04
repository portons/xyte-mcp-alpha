## Fix-up Road-map — “deployment-setup” Branch

This checklist converts the audit findings into **actionable work units**.  Each task block shows:

* **What** the agent edits or adds
* **Why** it matters (security, reliability, clarity)
* **Key acceptance hints** so tests/docs can prove it’s done.

> **Scope legend**
> `PY` = Python source edit `DOCKER` = Dockerfile
> `HELM` = Helm chart/templates `DOC` = Markdown/README
> `CI` = GitHub Actions / tests

---

### 1  Introduce Multi-Tenant Authentication

| #   | File(s)                                           | What to do                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Why / Acceptance                                                                                                                                                           |
| --- | ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.1 | `src/xyte_mcp/auth.py` (PY)                 | Create **AuthHeaderMiddleware**.<br>Logic:  <br>• Bypass only `/healthz`, `/readyz`, `/metrics`.  <br>• If `settings.xyte_api_key` **is `None`** → *multi-tenant mode*:  <br>  – Read `Authorization` header (raw Xyte key).  <br>  – 401 JSON error when missing/empty.  <br>• Store key in `request.state.xyte_key = header_val`.<br>• If `settings.xyte_api_key` **is not None** → *single-tenant*: header optional; if present and ≠ env key, 403 JSON `{"error":"invalid_token"}`. | Guarantees every request carries a key in hosted deployments while preserving local DX. <br>**Accept**: Curl without header = 401 when no env key. Curl with header = 200. |
| 1.2 | `src/xyte_mcp/http.py` (PY)                 | `app.add_middleware(AuthHeaderMiddleware)` directly after CORS middleware.                                                                                                                                                                                                                                                                                                                                                                                                              | Activates enforcement globally.                                                                                                                                            |
| 1.3 | `src/xyte_mcp/deps.py` (or existing helper) | Refactor `get_client(request: Request)` to:  <br>`key = request.state.xyte_key or settings.xyte_api_key` <br>Instantiate `XyteAPIClient(api_key=key)`.                                                                                                                                                                                                                                                                                                                                  | Unifies credential handling; call-sites no longer care where key came from.                                                                                                |
| 1.4 | **All resource & tool handlers** (PY)             | Ensure they now receive `Request` via FastAPI dependency injection and pass it to `get_client`. Example pattern:  <br>`async def list_devices(request: Request):`  <br>` async with get_client(request) as client:` ...                                                                                                                                                                                                                                                                 | Makes every handler multi-tenant aware.                                                                                                                                    |
| 1.5 | `tests/test_auth.py` (CI)                         | New parametrised tests:  <br>• mode = multi-tenant (no env key) + no header → 401  <br>• mode = multi-tenant + header → 200  <br>• mode = single-tenant (env key) + no header → 200  <br>• mode = single-tenant + wrong header → 403                                                                                                                                                                                                                                                    | Locks spec in test suite.                                                                                                                                                  |

---

### 2  Make `xyte_api_key` Optional & Advertise Mode

| #   | File(s)                             | What to do                                                                                                                                                                                             | Why / Acceptance                             |
| --- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------- |
| 2.1 | `src/xyte_mcp/config.py` (PY) | Change `xyte_api_key: str` → `Optional[str]`. Remove hard-fail in `validate_settings()`; instead:  <br>`if not self.xyte_api_key: logger.info("Running in multi-tenant mode")` else log single-tenant. | Allows container to boot without global key. |
| 2.2 | `.env.example` (DOC)                | Leave `XYTE_API_KEY=` blank; comment “leave blank for hosted mode”. List `XYTE_PLUGINS`, `XYTE_OAUTH_TOKEN`, `XYTE_USER_TOKEN`.                                                                        | Developers copy example with right defaults. |

---

### 3  Logging & CORS Hardening

| #   | File(s)                                                                                                                 | What / Why                                                                                                  |                                                                   |
| --- | ----------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| 3.1 | `RequestLoggingMiddleware` (PY)                                                                                         | Redact `Authorization` value: replace with `abcd****` before emitting log\_json.                            |                                                                   |
| 3.2 | `src/xyte_mcp/settings.py` (PY)                                                                                   | Add `allow_all_cors: bool = False` default. In `http.py`, configure CORS origins `["*"]` only if flag true. | Prevents wild-card CORS in production; devs can enable if needed. |
| 3.3 | Replace stray `logger.info(..., extra=...)` calls with `log_json` helper—or configure JSON formatter to include extras. | Keeps logs machine-parseable.                                                                               |                                                                   |

---

### 4  Docker & Helm Alignment

| #   | File(s)                                 | Action                                                                                                                                                                                                  | Why                                                    |
| --- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| 4.1 | `Dockerfile` (DOCKER)                   | Switch `CMD` from `["serve"]` to `["python","-m","xyte_mcp.http"]`. Add non-root user stage.                                                                                                      | Container now exposes HTTP :8080 matching Helm probes. |
| 4.2 | `helm/templates/deployment.yaml` (HELM) | Remove explicit `command:` override if present; rely on new Docker CMD.                                                                                                                                 | Prevent drift between image and chart.                 |
| 4.3 | `helm/values.yaml` + templates (HELM)   | Parameters:  <br>`multiTenant: true/false` (bool)  <br>`userToken`, `oauthToken` → mount as K8s Secret when non-empty. Chart logic:  <br>if `multiTenant` true then **omit** `XYTE_API_KEY` secret env. | Lets operators flip mode and supply alt creds cleanly. |
| 4.4 | Readiness/Liveness Probes               | Verify `/readyz` & `/healthz` on port 8080 succeed with new entrypoint. Update probe initialDelaySeconds if needed.                                                                                     |                                                        |

---

### 5  Async Task Strategy

| #   | File(s)                                                                                                                                                                                         | What to do                                    | Why |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- | --- |
| 5.1 | Add `ENABLE_ASYNC_TASKS` (Settings). Default `false`.                                                                                                                                           | Allows deployments without extra infra.       |     |
| 5.2 | In `tools/send_command_async`:  <br>if flag off, call `send_command` synchronously and return `{"status":"done","result":...}`.                                                                 | Ensures feature works without Celery.         |     |
| 5.3 | If flag on, integrate Celery:  <br>• broker from `REDIS_URL`, result backend from `RESULT_BACKEND_URL`.  <br>• Provide `docker-compose.celery.yaml` sample & Helm sub-chart for worker + Redis. | Makes background tasks persistent & scalable. |     |
| 5.4 | Docs: clearly list trade-offs & how to enable.                                                                                                                                                  |                                               |     |

---

### 6  Helm & Deployment Docs

| #   | File(s)                                                                                                                              | What / Why                                                                                                              |
| --- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| 6.1 | `docs/DEPLOYMENT.md` (DOC)                                                                                                           | New **Mode Matrix** table: single-tenant vs multi-tenant vs multi-tenant+Celery. Include sample `values.yaml` snippets. |
| 6.2 | README quick-start: two subsections “Local / single-tenant” and “Cloud / multi-tenant”. Include `curl` of `/v1/devices` with header. |                                                                                                                         |
| 6.3 | `.env.example` comments: flag meaning, async toggle, plugin path.                                                                    |                                                                                                                         |
| 6.4 | `docs/PLUGINS.md` mention `XYTE_PLUGINS` env.                                                                                        |                                                                                                                         |

---

### 7  CI Matrix & Strict Typing

| #   | File(s)                                                                   | Action                                                                                                           |                                           |
| --- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| 7.1 | `.github/workflows/ci.yml` (CI)                                           | Add job strategy:  <br>• `env XYTE_API_KEY=dummy` (single)  <br>• no `XYTE_API_KEY` + tests send header (multi). |                                           |
| 7.2 | Remove \`                                                                 |                                                                                                                  | true\` from MyPy step; fix typing errors. |
| 7.3 | Add Bandit/Trivy fail-on-critical option; break build on vulnerabilities. |                                                                                                                  |                                           |

---

### 8  Minor Clean-ups

| #   | Item                                                                                   | What                                        |
| --- | -------------------------------------------------------------------------------------- | ------------------------------------------- |
| 8.1 | In-memory user-prefs demo                                                              | Comment header: “demo only, not persisted”. |
| 8.2 | Remove or guard `/v1/device_logs` placeholder behind `enable_experimental_apis`.       |                                             |
| 8.3 | Ensure `.env.example` lists `XYTE_ALLOW_ALL_CORS=false` default to nudge safe posture. |                                             |

---

## Acceptance Checklist (copy into PR description)

* [ ] Per-request key auth enforced & tested.
* [ ] Server boots with **no** `XYTE_API_KEY` and returns 401 on unauth’d calls.
* [ ] Docker image runs HTTP server, probes green under Helm.
* [ ] Helm `multiTenant=true` deploys without global secret.
* [ ] Async toggle works: sync fallback when disabled; Celery worker job chart included.
* [ ] CI matrix passes all tests, coverage ≥ 95 %.
* [ ] No `Authorization` value appears in container logs (checked via test capture).
* [ ] README / DEPLOYMENT docs list mode matrix & updated commands.

Ship these fixes and the MCP repo will satisfy enterprise-grade deployment, local ad-hoc usage, and your bonus requirements.
