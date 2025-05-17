## General Codebase Health

* [ ] Ensure 100% test coverage (unit + integration), covering edge cases and error handling

* [ ] Parameterize repetitive tests for all MCP scenarios

* [ ] Set up CI for PR lint/test enforcement

* [ ] Add end-to-end tests for server lifecycle: start, registration, discovery, command flow, telemetry

* [ ] Enforce black/ruff/flake8 formatting across all code

* [ ] Achieve full mypy coverage, fix type/lint issues

* [ ] Fix discovered lint/type issues in scripts, server, and utils

---

## MCP Protocol Compliance & Server Feature Parity

* [ ] Verify MCP API adherence for all endpoints (cross-check with MCP 1.9.0 spec)

* [ ] Implement versioned API routing

* [ ] Add OpenAPI schema docs with live generation

* [ ] Ensure device discovery, claiming, updating, and deletion match MCP spec exactly

* [ ] Implement robust device event streaming (SSE/WebSocket fallback as needed)

* [ ] Fully implement command send/cancel/query lifecycle (all state transitions)

* [ ] Implement ticketing endpoints, matching input/output schemas

---

## Extensibility & Integration

* [ ] Validate mapping of all MCP flows to XYTE’s external API (configurable, not hardcoded)
* [ ] Allow for custom mapping/transform hooks (pluggable Python, securely sandboxed)

---

## Authentication & Security

* [ ] Ensure API key or OAuth2 support (user-supplied key)
* [ ] Validate all inbound and outbound payloads
* [ ] Harden HTTP endpoints (rate limiting, input validation, CORS, etc.)

---

## Observability & Ops

* [ ] Implement structured (JSON) logging with context (request/correlation IDs)

* [ ] Add logging for all state transitions, errors, and critical flows

* [ ] Add Prometheus metrics for critical events (requests, errors, device/command counts, latency)

* [ ] Health and readiness endpoints for ops (K8s) use

---

## Deployment & Infrastructure

* [ ] Ensure Dockerfile is production-ready (multi-stage, non-root user, no build deps in image)

* [ ] Add/verify K8s manifests (deployment, service, configmap/secret for keys)

* [ ] Document all env vars in README and Helm values.yaml

* [ ] Use pydantic for config parsing, with `.env` file support

* [ ] Expose safe config via `/config` (protected) endpoint for ops debugging

---

## Developer Experience

* [ ] Update README with quickstart, XYTE-specific config, and troubleshooting

* [ ] Maintain full API spec in docs/spec.md (auto-generated)

* [ ] Add Postman collection and curl examples for all endpoints

* [ ] Provide sample plugin (hook) for transforming MCP payloads

* [ ] Example: adding a new “resource” type and command

---

## Code Quality/Architecture

* [ ] Refactor utility, model, and client files to minimize duplication (single source of truth for types)

* [ ] Remove dead code and unused imports/functions

* [ ] Add retries with exponential backoff for all external XYTE API calls

* [ ] Implement circuit breaker/fallback for backend downtime (graceful errors)

---

## Compliance & Ecosystem

* [ ] Set up regular dependency update checks and security PR automation
* [ ] Annually review MCP spec for changes and update roadmap

---

## Future-Ready

* [x] Prepare hooks for AI agent integration (eventing/logging/plugin interfaces)
* [x] Allow feature flags for experimental APIs
