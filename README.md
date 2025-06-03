# Xyte MCP Server

![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)
![CI](https://github.com/portons/xyte-mcp-alpha/actions/workflows/ci.yml/badge.svg)
[![Codecov](https://codecov.io/gh/portons/xyte-mcp-alpha/branch/main/graph/badge.svg)](https://codecov.io/gh/portons/xyte-mcp-alpha)

An **MCP (Model Context Protocol) server** that bridges AI assistants (or other HTTP clients) with the **Xyte Organization API**.  
It exposes Xyte resources as clean URIs, wraps privileged actions as “tools”, and adds observability, rate-limiting and plugin hooks so you can **query devices, run commands, manage tickets and stream events — all from a single, AI-friendly endpoint**.

---

## Table of Contents

- [Quick-start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Server](#running-the-server)
- [Features](#features)
- [Deployment Guide](#deployment-guide)
  - [Docker / ECS Fargate](#1-docker--ecs-fargate)
  - [Kubernetes / Helm](#2-kubernetes--helm)
  - [Other Platforms](#3-other-platforms)
- [Security & Best Practices](#security--best-practices)
- [Maintenance & Scaling](#maintenance--scaling)
- [Integrations (Claude Desktop)](#integrations-claude-desktop)
- [Logging & Monitoring](#logging--monitoring)
- [Development](#development)
- [API Reference](#api-reference)
- [For CODEX](#for-codex)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [License](#license) · [Contributing](#contributing) · [Support](#support) · [Plugin API](#plugin-api)

---

## Quick-start

```bash
git clone https://github.com/portons/xyte-mcp-alpha.git
cd xyte-mcp-alpha
python -m venv venv && source venv/bin/activate
pip install -e .
cp .env.example .env          # edit XYTE_API_KEY inside
serve                         # or: python -m xyte_mcp_alpha.http
````

The HTTP server listens on **[http://127.0.0.1:8080/v1](http://127.0.0.1:8080/v1)** (configure host/port via env vars).

---

## Installation

```bash
# Editable install for development
pip install -e ".[dev]"

# Production install (from PyPI once released)
pip install xyte-mcp
```

---

## Configuration

| Variable                 | Required | Default                                    | Description                                          |
| ------------------------ | -------- | ------------------------------------------ | ---------------------------------------------------- |
| `XYTE_API_KEY`           | **Yes**  | —                                          | Org-level key for Xyte Cloud                         |
| `XYTE_USER_TOKEN`        | No       | —                                          | User token (overrides API key for user-scoped calls) |
| `XYTE_OAUTH_TOKEN`       | No       | —                                          | OAuth2 token alternative                             |
| `XYTE_BASE_URL`          | No       | `https://hub.xyte.io/core/v1/organization` | Use staging / custom endpoint                        |
| `XYTE_CACHE_TTL`         | No       | `60`                                       | Cache lifetime (seconds) for Xyte GETs               |
| `XYTE_RATE_LIMIT`        | No       | `60`                                       | Requests per minute, per instance                    |
| `XYTE_ENV`               | No       | `prod`                                     | Free-form environment label                          |
| `XYTE_LOG_LEVEL`         | No       | `INFO`                                     | `DEBUG`, `INFO`, `WARNING`, …                        |
| `MCP_INSPECTOR_HOST`     | No       | `127.0.0.1`                                | Bind host (`0.0.0.0` for public)                     |
| `MCP_INSPECTOR_PORT`     | No       | `8080`                                     | Bind port                                            |
| `XYTE_PLUGINS`           | No       | —                                          | Comma-separated list of plugins                      |
| `XYTE_EXPERIMENTAL_APIS` | No       | `false`                                    | Enable experimental endpoints                        |

Save these in **.env** or inject through your orchestrator / secret-manager.

---

## Running the Server

| Mode                | Command                                   | Use-case                                            |
| ------------------- | ----------------------------------------- | --------------------------------------------------- |
| **Stdio MCP**       | `serve`                                   | Spawned by an AI agent runner (e.g. Claude Desktop) |
| **HTTP API**        | `python -m xyte_mcp_alpha.http`           | Stand-alone service (cURL / browser)                |
| **Inspector (dev)** | `mcp dev src/xyte_mcp_alpha/server.py`    | Interactive REPL & auto-reload                      |
| **Docker**          | See [Deployment Guide](#deployment-guide) | Container / cloud                                   |

---

## Features

### Resources (read-only)

* `devices://` - List all devices
* `device://{id}/status` - Current status
* `device://{id}/commands` - Available commands
* `device://{id}/histories` - History records
* `organization://info/{id}` - Org info for device context
* `incidents://` - All incidents
* `tickets://` - All support tickets
* `ticket://{id}` - Single ticket
* `user://{token}/devices` & `…/preferences` - User-filtered queries

### Tools (actions)

| Tool                                                           | Purpose                                |
| -------------------------------------------------------------- | -------------------------------------- |
| `claim_device`                                                 | Register device                        |
| `delete_device`                                                | Remove device                          |
| `update_device`                                                | Patch configuration                    |
| `send_command`, `send_command_async`                           | Immediate / async commands             |
| `cancel_command`                                               | Abort command                          |
| `search_device_histories`                                      | Filter / search                        |
| `update_ticket`, `mark_ticket_resolved`, `send_ticket_message` | Ticket ops                             |
| `get_task_status`                                              | Poll async task                        |
| `set_context`                                                  | Store default `device_id` / `space_id` |
| `get_device_analytics_report`                                  | Advanced analytics                     |
| `start_meeting_room_preset`, `shutdown_meeting_room`           | Room presets                           |

*All tools accept `dry_run=true` for safe previews.*

### Event Streaming

* `POST /v1/webhook` – push external events
* `GET  /v1/events` – Server-Sent Events stream

### Observability

* `/v1/healthz` & `/v1/readyz` – liveness/readiness
* `/v1/metrics` – Prometheus metrics

---

## Deployment Guide

### 1. Docker / ECS-Fargate

```bash
docker build -t xyte-mcp .
docker run -d -p 8080:8080 \
  -e XYTE_API_KEY=$XYTE_API_KEY \
  --entrypoint "python" xyte-mcp -m xyte_mcp_alpha.http
```

Push to **ECR**, create an **ECS Fargate** service, set env vars in the task definition, front with an **ALB** (HTTPS).

### 2. Kubernetes / Helm

```bash
helm install xyte ./helm \
  --set env.XYTE_API_KEY=$XYTE_API_KEY \
  --set service.type=LoadBalancer
```

* Secrets as `Secret`; non-sensitive env in `ConfigMap`.
* Scale out: `helm upgrade xyte ./helm --set replicaCount=3`.
* Health probes & Prometheus annotations included.

### 3. Other Platforms

Any place that runs Docker or Python 3.11: Fly.io, Render, Railway, Azure Container Apps, Google Cloud Run, plain VM + systemd, etc.

---

## Security & Best Practices

1. **Do not expose unauthenticated.** Use private networking or an auth gateway.
2. **Least-privilege**: prefer `XYTE_USER_TOKEN` when possible.
3. **Rotate secrets**; restart pods/containers to reload.
4. **Rate-limit** with `XYTE_RATE_LIMIT` (defaults to 60 RPM).
5. Runs as non-root; keep base image patched.
6. Terminate **TLS** at a reverse proxy / load balancer.

---

## Maintenance & Scaling

* **Stateless** → scale horizontally behind a load balancer.
* In-memory event queue/cache - replicate or externalise if you need global ordering.
* Prometheus metrics (`xyte_request_latency_seconds`, `xyte_errors_total`) and Grafana dashboard (`docs/grafana_dashboard.json`).
* Upgrade via Helm or rolling container replace; follows semver (`1.x.y`).
* Run `pytest` in CI – coverage badge stays 100 %.

---

## Integrations (Claude Desktop)

Add to `~/.claude/config.json` (or `%APPDATA%` on Windows):

```json
{
  "mcpServers": {
    "xyte": {
      "command": "serve",
      "env": { "XYTE_API_KEY": "your-api-key" }
    }
  }
}
```

Use `python -m xyte_mcp_alpha.http` if you prefer HTTP mode.

---

## Logging & Monitoring

Structured JSON logs (`request_id` per call) to **stderr**.
Set `XYTE_LOG_LEVEL=DEBUG` for verbosity.
Prometheus at `/v1/metrics`; probes at `/v1/healthz` & `/v1/readyz`.

---

## Development

```bash
pip install -e ".[dev]"
mcp dev src/xyte_mcp_alpha/server.py   # live reload & inspector
pytest                                 # full test suite
```

Custom inspector port if 6277 is taken:

```bash
MCP_INSPECTOR_PORT=6278 mcp dev src/xyte_mcp_alpha/server.py
```

---

## API Reference

Generate an OpenAPI spec:

```bash
XYTE_API_KEY=your-key scripts/generate_openapi.py
```

Swagger UI auto-mounts at **/v1/docs** (HTTP mode).

| Xyte Status   | MCP Error           |
| ------------- | ------------------- |
| `401`         | `unauthorized`      |
| `404`         | `not_found`         |
| `429`         | `rate_limited`      |
| `5xx`         | `xyte_server_error` |
| Network issue | `network_error`     |

---

## For CODEX

Setup commands live in `/.setup/install.txt`. **Read them** and execute in order; they only install packages, no code modification or external network access.

---

## Examples

**Python**

```python
import os, requests, json
resp = requests.get(
    "http://localhost:8080/v1/devices",
    headers={"Authorization": os.environ["XYTE_API_KEY"]}
)
print(json.dumps(resp.json(), indent=2))
```

**cURL**

```bash
curl -H "Authorization: $XYTE_API_KEY" \
     http://localhost:8080/v1/devices
```

---

## Troubleshooting

| Symptom                   | Resolution                                             |
| ------------------------- | ------------------------------------------------------ |
| `unauthorized`            | Verify `XYTE_API_KEY` / token scope                    |
| `rate_limited` (429)      | Lower QPS or raise `XYTE_RATE_LIMIT` (within plan)     |
| No events on `/v1/events` | Verify same pod / use shared broker                    |
| High latency              | Increase cache TTL, check Xyte API latency via metrics |

---

## License

MIT

## Contributing

PRs and issues welcome — keep tests green and coverage 100 %.

## Support

See **SUPPORT.md** for contact info and responsible-disclosure policy.

## Plugin API

Plugins must declare `PLUGIN_API_VERSION` matching the server’s version.
Hook signatures: `on_event(event)` and `on_log(record)`.
See **docs/plugin\_api\_version.md**.
