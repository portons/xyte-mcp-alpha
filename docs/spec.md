## General Codebase Health

* [x] Ensure 100% test coverage (unit + integration), covering edge cases and error handling

* [x] Parameterize repetitive tests for all MCP scenarios

* [x] Set up CI for PR lint/test enforcement

* [x] Add end-to-end tests for server lifecycle: start, registration, discovery, command flow, telemetry

* [x] Enforce black/ruff/flake8 formatting across all code

* [x] Achieve full mypy coverage, fix type/lint issues

* [x] Fix discovered lint/type issues in scripts, server, and utils

---

## MCP Protocol Compliance & Server Feature Parity

* [ ] Verify MCP API adherence for all endpoints (cross-check with MCP 1.9.0 spec)

* [x] Implement versioned API routing

* [x] Add OpenAPI schema docs with live generation

* [x] Ensure device discovery, claiming, updating, and deletion match MCP spec exactly

* [x] Implement robust device event streaming (SSE/WebSocket fallback as needed)

* [x] Fully implement command send/cancel/query lifecycle (all state transitions)

* [x] Implement ticketing endpoints, matching input/output schemas

---

## Extensibility & Integration

* [x] Validate mapping of all MCP flows to XYTE’s external API (configurable, not hardcoded)
* [x] Allow for custom mapping/transform hooks (pluggable Python, securely sandboxed)

---

## Authentication & Security

* [x] Ensure API key or OAuth2 support (user-supplied key)
* [x] Validate all inbound and outbound payloads
* [x] Harden HTTP endpoints (rate limiting, input validation, CORS, etc.)

---

## Observability & Ops

* [x] Implement structured (JSON) logging with context (request/correlation IDs)

* [x] Add logging for all state transitions, errors, and critical flows

* [x] Add Prometheus metrics for critical events (requests, errors, device/command counts, latency)

* [x] Health and readiness endpoints for ops (K8s) use

---

## Deployment & Infrastructure

* [x] Ensure Dockerfile is production-ready (multi-stage, non-root user, no build deps in image)

* [x] Add/verify K8s manifests (deployment, service, configmap/secret for keys)

* [x] Document all env vars in README and Helm values.yaml

* [x] Use pydantic for config parsing, with `.env` file support

* [x] Expose safe config via `/config` (protected) endpoint for ops debugging

---

## Developer Experience

* [x] Update README with quickstart, XYTE-specific config, and troubleshooting

* [x] Maintain full API spec in docs/spec.md (auto-generated)

* [x] Add Postman collection and curl examples for all endpoints

* [x] Provide sample plugin (hook) for transforming MCP payloads

* [x] Example: adding a new “resource” type and command

---

## Code Quality/Architecture

* [x] Refactor utility, model, and client files to minimize duplication (single source of truth for types)

* [x] Remove dead code and unused imports/functions

* [x] Add retries with exponential backoff for all external XYTE API calls

* [x] Implement circuit breaker/fallback for backend downtime (graceful errors)

---

## Compliance & Ecosystem

* [ ] Set up regular dependency update checks and security PR automation
* [ ] Annually review MCP spec for changes and update roadmap

---

## Future-Ready

* [ ] Prepare hooks for AI agent integration (eventing/logging/plugin interfaces)
* [ ] Allow feature flags for experimental APIs

### OpenAPI Specification

The MCP server exposes a documented OpenAPI schema. Regenerate it with:

```bash
curl http://localhost:8080/openapi.json > docs/openapi.json
```

The source specification is stored in `registry.yaml` for reference.
