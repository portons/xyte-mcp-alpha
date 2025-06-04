# Deployment Guide

This project provides a Helm chart and raw Kubernetes manifests for deploying the
MCP server.

## Installing with Helm

1. Ensure you have `helm` installed and access to a Kubernetes cluster.
2. If running single-tenant, set the API key and install the chart:
   ```bash
   helm install xyte ./helm \
     --set env.XYTE_API_KEY=YOUR_KEY
   ```
3. Override `image.repository` or `image.tag` if you push a custom image.

## Deployment Modes

The chart can run in three modes depending on your credentials and whether you
use Celery for background tasks.

| Mode | multiTenant | XYTE_API_KEY | ENABLE_ASYNC_TASKS | Notes |
|------|-------------|--------------|--------------------|------|
| Single-tenant | `false` | set | `false` | API key baked into the pod |
| Multi-tenant | `true` | omit | `false` | Each request supplies the key |
| Multi-tenant + Celery | `true` | omit | `true` | Requires worker and Redis |

### Sample `values.yaml`

Single-tenant:

```yaml
multiTenant: false
env:
  XYTE_API_KEY: "your-key"
```

Multi-tenant:

```yaml
multiTenant: true
```

Multi-tenant with Celery:

```yaml
multiTenant: true
env:
  ENABLE_ASYNC_TASKS: "true"
worker:
  enabled: true
```

## Key Values

- **image.repository** – Docker image to run.
- **image.tag** – Image tag, defaults to `latest`.
- **service.type** – Service type (`ClusterIP`, `LoadBalancer`, etc.).
- **env.*** – Environment variables passed through to the container.

See `helm/values.yaml` for the full list of configurable options.

## Raw Manifests

The `k8s/` directory contains plain manifests matching the chart. Apply them
with `kubectl apply -f k8s/` if you prefer not to use Helm.

## Upgrades and Rollbacks

Upgrade the release with:
```bash
helm upgrade xyte ./helm -f my-values.yaml
```
If something goes wrong you can roll back:
```bash
helm rollback xyte
```

## docker-compose Example

This repo ships a `docker-compose.yml` that starts the MCP server, Redis,
Postgres and a Celery worker. Set `ENABLE_ASYNC_TASKS=true` to activate
background processing:

```yaml
version: '3.9'
services:
  mcp:
    image: ghcr.io/xyte/mcp:latest
    environment:
      REDIS_URL: "redis://redis:6379/0"
      DATABASE_URL: "postgresql+asyncpg://mcp:pass@pg/mcp"
      ENABLE_ASYNC_TASKS: "true"
    depends_on: [redis, pg]
  redis:
    image: redis:7
  pg:
    image: postgres:15
    environment:
      POSTGRES_DB: mcp
      POSTGRES_USER: mcp
      POSTGRES_PASSWORD: pass
  worker:
    image: ghcr.io/xyte/mcp:latest
    command: celery -A xyte_mcp_alpha.celery_app worker -Q long -c 2
    environment:
      REDIS_URL: "redis://redis:6379/0"
      DATABASE_URL: "postgresql+asyncpg://mcp:pass@pg/mcp"
      ENABLE_ASYNC_TASKS: "true"
```

### Async Task Strategy

When `ENABLE_ASYNC_TASKS` is disabled the `send_command_async` tool simply
executes the command synchronously and returns the result. Enabling the flag
requires running Redis and a Celery worker (see sample `docker-compose.celery.yaml`)
and tasks will persist across restarts.


## Health Probes

Include the following liveness and readiness probes in your deployment:

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
readinessProbe:
  httpGet:
    path: /readyz
    port: 8080
```
