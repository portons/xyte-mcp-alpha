### Detailed Work Plan — XYTE MCP Server “Local + Multi-Tenant” Upgrade

This roadmap breaks every change into **purpose → action → rationale** blocks, so an implementation agent always knows *what to do* and *why it matters*.
No branch-flow instructions are included—just the work itself.

---

## 1  Configuration Layer

| Step | Action                                                                                                                                       | Rationale                                                                                     |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| [x] 1.1 | Convert `Settings.xyte_api_key` from **required** → **optional** (`str \| None`).                                                            | Allows the service to run without a baked-in key when operating in hosted, multi-tenant mode. |
| [x] 1.2 | Add computed property `settings.multi_tenant = xyte_api_key is None`.                                                                        | Gives downstream code a single flag to switch behaviour.                                      |
| [x] 1.3 | In `validate_settings()`: remove the “API key must exist” hard-fail. Instead, log whether we boot in single- or multi-tenant mode.           | Keeps dev UX unchanged while removing the blocker for multi-tenant deployments.               |
| [x] 1.4 | Update `.env.example` & README configuration table so `XYTE_API_KEY` is blank by default and clearly labelled “leave empty for hosted mode”. | Prevents accidental single-tenant assumptions in production.                                  |

---

## 2  Request Authentication

| Step | Action                                                                                                                                                                                                                                           | Rationale                                                                                         |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| [x] 2.1 | Implement `AuthHeaderMiddleware` (Starlette). Logic:  <br>• skip `/healthz`, `/readyz`, `/metrics`  <br>• if `settings.multi_tenant` **require** `Authorization` header (raw Xyte key) else 401  <br>• store header in `request.state.xyte_key`. | Enforces per-request credentials only when the build actually needs them—no duplicate code paths. |
| [x] 2.2 | Sanitize logs inside existing `RequestLoggingMiddleware`: mask `Authorization` values (e.g., `abcd****`).                                                                                                                                        | Prevents accidental secret disclosure in central logging.                                         |
| [x] 2.3 | Wire middleware into app in `http.py`.                                                                                                                                                                                                           | Central location keeps bootstrapping predictable.                                                 |

---

## 3  Xyte API Client Injection

| Step | Action                                                                                                                                               | Rationale                                                                        |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| 3.1  | Extend `deps.get_client()` signature to accept `Request`; resolve key:  <br>`key = request.state.xyte_key or settings.xyte_api_key`.                 | Single function now covers both modes—call-sites don’t need to think about auth. |
| 3.2  | Refactor every resource/tool/task that currently calls `get_client()` to pass `request` (use dependency injection where FastAPI routes are defined). | Keeps call signatures explicit but lightweight; no hidden globals.               |
| 3.3  | Delete any accidental use of `settings.xyte_api_key` elsewhere in code except as the single-tenant fallback.                                         | Guarantees header override always wins in multi-tenant mode.                     |

---

## 4  Clean-up Legacy Paths & Placeholders

| Step | Action                                                                                                                                                                           | Rationale                                                                                             |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 4.1  | **`user_token` routes**: treat token purely as a local filter key (preferences), never as an auth credential. Replace `get_client(user_token)` with plain `get_client(request)`. | Removes broken assumption that `user_token` was a valid Xyte key while preserving demo functionality. |
| 4.2  | Wrap `device_logs` and other stub endpoints behind `settings.enable_experimental_apis`. Disable by default.                                                                      | Users can’t trip on half-baked features in production, but devs keep a toggle for future work.        |
| 4.3  | Restrict `/config` debug endpoint to `settings.multi_tenant is False` *and* a matching header. Optionally remove entirely.                                                       | Prevents a mis-configured cloud deployment from leaking environment details.                          |

---

## 5  Security Hardening

| Step | Action                                                                                                                                                                   | Rationale                                                                           |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| 5.1  | Create `SECURITY.md`:  <br>• disclosure process  <br>• TLS-only recommendation  <br>• secret-management pointers (K8s Secrets, .env not committed).                      | Gives ops clear guidance and satisfies basic open-source hygiene.                   |
| 5.2  | Dockerfile cleanup:  <br>• multi-stage build  <br>• run as non-root user  <br>• `CMD ["python", "-m", "xyte_mcp_alpha.http"]`.                                           | Shrinks image, aligns with container best practices, prevents privilege-escalation. |
| 5.3  | Helm chart: add `securityContext` (`runAsNonRoot`, `fsGroup`), make `XYTE_API_KEY` optional, add `multiTenant: true` flag that toggles auth middleware config in values. | Secure defaults + one-line switch between single/multi tenant deployments.          |
| 5.4  | Confirm every structured log helper redacts secrets; add test that asserts no key strings appear in captured logs during request cycle.                                  | Stops regressions in future logging changes.                                        |

---

## 6  Documentation Overhaul

| Step | Action                                                                                                                                                                                   | Rationale                                                 |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| 6.1  | **README**: replace single quick-start with dual-mode table:  <br>Local (single-tenant) vs Hosted (multi-tenant) → prerequisites, env vars, auth pattern, example `curl`.                | New users immediately see which path applies to them.     |
| 6.2  | Expand `docs/DEPLOYMENT.md`:  <br>• docker-compose (app + Redis + Postgres + Celery worker)  <br>• Helm multi-tenant values snippet  <br>• liveness/readiness probe examples.            | Gives operators copy-paste manifests for any environment. |
| 6.3  | Write `docs/API_USAGE.md`: for each exposed resource/tool, include:  <br>– purpose  <br>– HTTP verb/route  <br>– minimal request  <br>– canonical JSON response  <br>– edge-case errors. | Lets agents craft correct calls without spelunking code.  |
| 6.4  | Update `docs/PLUGINS.md`: plugin skeleton, registration via `XYTE_PLUGINS`, warning about untrusted code.                                                                                | Encourages safe extensibility.                            |

---

## 7  Test-Suite Expansion

| Step | Action                                                                                                                                         | Rationale                                        |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| 7.1  | Parametrized auth tests:  <br>• multi-tenant + missing header ⇒ 401  <br>• multi-tenant + header ⇒ 200  <br>• single-tenant + no header ⇒ 200. | Locks in the new contract.                       |
| 7.2  | Mocked httpx verification: assert forwarded `Authorization` matches incoming header for multi-tenant and matches env key for single-tenant.    | Prevents silent regressions in auth propagation. |
| 7.3  | Capture logs in test; assert masked keys (e.g., `'****'` present, raw key absent).                                                             | Guarantees log-sanitizer works.                  |
| 7.4  | Maintain coverage ≥ 95 %. Update CI threshold.                                                                                                 | Forces new code to be tested.                    |

---

## 8  CI/CD Enhancements

| Step | Action                                                                                                               | Rationale                                               |
| ---- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| 8.1  | CI matrix: run full test-suite twice—once with `XYTE_API_KEY=dummy` (single-tenant) and once without (multi-tenant). | Ensures both modes compile and pass tests.              |
| 8.2  | Add Ruff + mypy jobs; fail on warnings.                                                                              | Automatic style/type discipline.                        |
| 8.3  | Build Docker image on every tag; push to GHCR; attach image digest as workflow output.                               | Gives ops a reproducible artifact without manual steps. |
| 8.4  | Dependabot configs for Python, Dockerfile, GitHub Actions.                                                           | Continuous security updates.                            |

---

## 9  Async-Task Toggle (Optional but Valuable)

| Step | Action                                                                                                             | Rationale                                                            |
| ---- | ------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| 9.1  | Introduce `ENABLE_ASYNC_TASKS` env var (default `false`).                                                          | Makes heavy Celery/DB stack opt-in.                                  |
| 9.2  | Wrap `send_command_async` entrypoint: if disabled, return deterministic JSON error (`{"error":"async_disabled"}`). | API remains stable; users get clear feedback instead of stack-trace. |
| 9.3  | Extend docs with compose/Helm snippets spinning up Redis + Worker when async enabled.                              | Smooth path for those who need background operations.                |

---

## 10  Release Criteria & Final Polishing

| Criterion                                                                            | Why it matters             |
|--------------------------------------------------------------------------------------| -------------------------- |
| [ ] README quick-start commands succeed verbatim in both modes.                      | First-impression fidelity. |
| [ ] All tests green, coverage ≥ 95 %.                                                | Regression safety net.     |
| [ ] Helm install (`multiTenant=true`) passes readiness probes in < 20 s.             | Deployment confidence.     |
| [ ] No secret substrings found in runtime logs under test.                           | Confidentiality assurance. |
| [ ] Docker image starts as non-root, listens on `0.0.0.0`, exits cleanly on SIGTERM. | Container best practice.   |

After these boxes tick, tag **v1.0.0** and ship.

---

### Implementation Notes for the Agent

* **Sequence Dependency:** Sections 1 → 2 → 3 must be implemented in order; everything else can proceed in parallel once those are stable.
* **Guard Rails:** Keep edits surgical—avoid re-architecting beyond scope. If an external dependency forces a larger change, record it in CHANGELOG and adjust tests first.
* **Fallback Strategy:** Commit after each main section; if any later test fails, bisect quickly.

Delivering on this checklist yields a clean, two-mode, production-ready MCP server that’s easy for any AI—or human—to extend and operate.
