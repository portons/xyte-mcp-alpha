## XYTE MCP Server — Implementation Road-Map

> **Goal**
> A rock-solid, production-grade MCP server that runs **locally** with a single Xyte API key *and* **hosted** in multi-tenant mode (per-request API key).
> This plan is split into concrete, bite-sized tasks an AI agent (or human) can execute top-to-bottom.

---

### 0. Project Kick-off

| #   | Task                                                                                                                   | Outcome                          |
| --- | ---------------------------------------------------------------------------------------------------------------------- | -------------------------------- |
| 0.1 | Create a working branch `feat/multi-tenant-1.0` off `deployment-setup`.                                                | Dedicated space for all changes. |
| 0.2 | Enable pre-commit (`pre-commit install`) with **ruff**, **black**, **isort**, **mypy**. Add `.pre-commit-config.yaml`. | Style/typing guard from day one. |
| 0.3 | Update `CHANGELOG.md` placeholder ➜ heading **“Unreleased – v1.0.0”**.                                                 | Track progress.                  |

---

### 1. Configuration Layer

| #   | Task                                                           | Details                                                   |                                                                                                                                                                                            |
| --- | -------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1.1 | **Settings refactor** (`config.py`)                            | • Add field \`xyte\_api\_key: str                         | None`(optional)  <br>• Add computed property`multi\_tenant = xyte\_api\_key is None`<br>• Emit log on startup:`Running in {'multi' if settings.multi\_tenant else 'single'}-tenant mode\`. |
| 1.2 | Remove hard fail in `validate_settings()` when key is missing. | For multi-tenant mode.                                    |                                                                                                                                                                                            |
| 1.3 | `.env.example` refresh                                         | List *all* vars; blank `XYTE_API_KEY`.                    |                                                                                                                                                                                            |
| 1.4 | Helm chart (`values.yaml`)                                     | Make `env.XYTE_API_KEY` optional. Add \`multiTenant: true | false\` value that sets/unsets the secret.                                                                                                                                                 |

---

### 2. Request Authentication Middleware

| #   | Task                                                                                                         | Details                                                                                                                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2.1 | New file `auth.py` with middleware `AuthHeaderMiddleware`.                                                   | • Skip `/healthz`, `/readyz`, `/metrics`. <br>• If `settings.multi_tenant`: require `Authorization` header, else raise `HTTP_401`. <br>• Store header value in `request.state.xyte_key`. |
| 2.2 | Add to `app.add_middleware(...)` in `http.py`.                                                               |                                                                                                                                                                                          |
| 2.3 | **Sanitize logs** in `RequestLoggingMiddleware`: strip `Authorization` header or show first 4 chars + `***`. |                                                                                                                                                                                          |

---

### 3. Xyte API Client Injection

| #   | Task                                                                                                                                                         | Details                                                                                                     |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| 3.1 | Modify `deps.get_client()`                                                                                                                                   | Accept `request: Request` param; pull key = `request.state.xyte_key` *or* `settings.xyte_api_key`.          |
| 3.2 | Update all call sites (`resources.py`, `tools/*.py`, `tasks.py`) to pass `request` or new helper `get_client_from_request(request)` to keep signatures tidy. |                                                                                                             |
| 3.3 | Unit tests: `tests/test_auth.py`                                                                                                                             | • Missing header ⇒ 401 when multi-tenant. <br>• Header present ⇒ 200. <br>• Single-tenant w/o header ⇒ 200. |

---

### 4. Clean-up Legacy / Placeholder Code

| #   | Task                                                                                                                                     | Action                                                                                                    |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| 4.1 | **`user_token` routes**                                                                                                                  | Convert to pure *filter* feature: always use resolved API key; `user_token` only indexes in-memory prefs. |
| 4.2 | Remove or hide `device_logs` placeholder route behind `settings.enable_experimental_apis`.                                               |                                                                                                           |
| 4.3 | Review `diagnose_av_issue`, `find_and_control_device` tools.  <br>• If alpha-only, flag them `experimental` and guard with same setting. |                                                                                                           |
| 4.4 | Drop `/config` endpoint or restrict to local dev (`settings.xyte_env != "prod"`).                                                        |                                                                                                           |

---

### 5. Security Hardening

| #   | Task                                                                            | Details                                                                                                                    |
| --- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 5.1 | Add `SECURITY.md`: responsible disclosure email, TLS reminder, secret handling. |                                                                                                                            |
| 5.2 | Dockerfile tweaks                                                               | • `USER appuser` (non-root). <br>• Multi-stage build to shrink image. <br>• `CMD ["python", "-m", "xyte_mcp_alpha.http"]`. |
| 5.3 | Helm chart securityContext: runAsNonRoot, fsGroup 1000.                         |                                                                                                                            |
| 5.4 | Mask API keys in all logs (double-check `log_json`).                            |                                                                                                                            |

---

### 6. Documentation Sprint

| #   | File                                         | What to add                                                                                                              |
| --- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| 6.1 | `README.md`                                  | • Clear “Local vs Hosted” quickstart table. <br>• Example curl with header. <br>• Link to DEPLOYMENT, PLUGINS, SECURITY. |
| 6.2 | `docs/DEPLOYMENT.md`                         | Helm multi-tenant values snippet; docker-compose sample (Postgres+Redis+worker).                                         |
| 6.3 | `docs/PLUGINS.md`                            | Minimal viable plugin template + warning about trusted code.                                                             |
| 6.4 | `docs/API_USAGE.md`                          | Sample request/response for devices, claim\_device tool, async task flow.                                                |
| 6.5 | Update diagrams / gif refs if paths changed. |                                                                                                                          |

---

### 7. Test Suite Expansion

| #   | Task                                                                                        | Details |
| --- | ------------------------------------------------------------------------------------------- | ------- |
| 7.1 | Add param-driven tests for single & multi-tenant modes (pytest `@pytest.mark.parametrize`). |         |
| 7.2 | Mock httpx calls to Xyte API; assert correct `Authorization` header forwarded.              |         |
| 7.3 | Integration smoke test: start app with TestClient, hit `/v1/devices` happy-path.            |         |
| 7.4 | Coverage target ≥ 95 %.                                                                     |         |

---

### 8. CI/CD Upgrade

| #   | Task                                                            | Details                                                                    |
| --- | --------------------------------------------------------------- | -------------------------------------------------------------------------- |
| 8.1 | `.github/workflows/ci.yml`                                      | • Add Ruff, mypy jobs. <br>• Matrix run: single-tenant & multi-tenant env. |
| 8.2 | Build & push Docker image on `tags/v*` to GHCR.                 |                                                                            |
| 8.3 | (Optional) Publish wheel to PyPI if `PYPI_TOKEN` present.       |                                                                            |
| 8.4 | Dependabot/renovate config for pip, Dockerfile, GitHub Actions. |                                                                            |

---

### 9. Async Task Path (Optional but Recommended)

| #   | Task                                                                    | Details  |
| --- | ----------------------------------------------------------------------- | -------- |
| 9.1 | Env toggles: \`ENABLE\_ASYNC\_TASKS=true                                | false\`. |
| 9.2 | If disabled, `send_command_async` returns `{"error":"async_disabled"}`. |          |
| 9.3 | Helm: separate Celery worker deployment YAML; docs update.              |          |
| 9.4 | Example Grafana dashboard import JSON for task metrics (optional).      |          |

---

### 10. Release 1.0 Checklist

1. **Code freezes** – all tasks complete, tests green, coverage ≥ 95 %.
2. Bump version in `__init__.py` ➜ `__version__ = "1.0.0"`.
3. Tag `v1.0.0`, trigger CI publish.
4. Update `CHANGELOG.md` (move “Unreleased” to “1.0.0 – YYYY-MM-DD”).
5. Announce internally / in repo README badge.

---

## Timeline Suggestion

| Week | Focus                             |
| ---- | --------------------------------- |
| 1    | Tasks 0 → 3 (core auth & config)  |
| 2    | Tasks 4 → 5 (clean-up & security) |
| 3    | Tasks 6 → 7 (docs + tests)        |
| 4    | Tasks 8 → 9, polish, release 1.0  |

---

### Done-Definition

*  [ ]  All routes enforce correct auth rules in both modes.
*  [ ]  README quickstart works copy-paste.
*  [ ]  Helm deploys with **multi-tenant** values and passes health checks.
*  [ ]  No API key ever printed in logs.
*  [ ]  CI green on PR, Docker image published on tag.

Copy this file into `docs/ROADMAP.md` (or similar), check boxes as you go, and the repo will end up a *presentable mfckn* production server.
