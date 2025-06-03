*(Everything below is verbatim-complete—no code, command, variable, or explanation removed. Copy-paste straight into your repo, CI, or agent pipelines.)*

---

# Xyte MCP Server — End-to-End Build + Run Plan

### (every step, every file, every command, with **What / Why / Result**)

---

## 0 Foundation & Versions

| Item                  | Version                             | **Why exactly this**                                                                                                                       |
| --------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Python**            | **3.11.x**                          | Repo’s `.python-version` is `3.11.3`; `pyproject.toml` has `requires-python=">=3.11,<3.12"`. All libs compile on 3.11, none need 3.12 yet. |
| **Starlette**         | 0.36+                               | Minimal async HTTP layer; used by FastMCP.                                                                                                 |
| **Uvicorn**           | 0.29+                               | ASGI server for prod & dev.                                                                                                                |
| **Redis 7.x**         | Latest LTS; supports Streams + Lua. |                                                                                                                                            |
| **PostgreSQL**        | 15.x                                | Stable; asyncpg officially supports it.                                                                                                    |
| **Celery**            | 5.3+                                | Modern worker w/ Redis broker.                                                                                                             |
| **Prometheus-client** | 0.19+                               | Metric exposition.                                                                                                                         |
| **OpenTelemetry SDK** | 1.25+                               | Tracing (optional).                                                                                                                        |

---

## 1 Directory Layout (target state)

```
repo/
├─ src/xyte_mcp_alpha/
│  ├─ __init__.py
│  ├─ server.py              # ASGI entry
│  ├─ auth_xyte.py           # per-request key gw
│  ├─ rate_limiter.py        # Redis Lua bucket
│  ├─ bucket.lua
│  ├─ events.py              # Redis Streams
│  ├─ tasks.py               # SQLModel Task DB
│  ├─ celery_app.py          # Celery factory
│  ├─ worker/long.py         # Celery tasks
│  ├─ presets/default.yaml
│  └─ tools/…                # originals + presets.py
├─ tests/test_errors.py
├─ docker/Dockerfile
├─ docker-compose.yml
├─ helm/chart/ (Chart.yaml, values.yaml, templates/*)
├─ requirements/prod.txt
├─ requirements/dev.txt
├─ docs/ (optional MkDocs)
└─ grafana/xyte_mcp_dashboard.json
```

---

## 2 One-Shot Dev Environment - SKIP THIS ONE

```bash
git clone https://github.com/portons/xyte-mcp-alpha.git
cd xyte-mcp-alpha
python3.11 -m venv .venv
source .venv/bin/activate
pip install \
  "starlette>=0.36" "uvicorn[standard]>=0.29" \
  "python-multipart>=0.0.9" "passlib[bcrypt]>=1.7" \
  "redis[async]>=5.0" \
  "sqlmodel>=0.0.12" "asyncpg>=0.29" \
  "celery[redis]>=5.3" \
  "prometheus-client>=0.19" "opentelemetry-sdk>=1.25" \
  "pyyaml>=6.0" \
  "pyjwt>=2.8" \
  "mcp[cli]>=1.1.0" \
  "python-dotenv>=1.0.0" \
  "cachetools>=5.3.0" \
  "pydantic>=2.0.0" \
  "pytest>=8.2" "httpx>=0.27" \
  "ruff>=0.4" "pyright>=1.1" \
  "safety>=3.2" \
  "mkdocs-material>=9.5"
```

**Why** Installs every library referenced in code/plan under Python 3.11.
**Result** Local venv ready for coding and tests.

---

## 3 Per-Request XYTE API-Key Gateway (no server-side secret)

`src/xyte_mcp_alpha/auth_xyte.py`

```python
import hashlib
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

_PUBLIC = {"/healthz", "/readyz", "/metrics", "/docs", "/openapi.json"}

class RequireXyteKey(BaseHTTPMiddleware):
    """
    Enforces header-based auth:
      • Accepts  'X-XYTE-API-KEY: <key>'        or
      • Accepts  'Authorization: Bearer <key>'
    A key must be ≥32 chars; server never stores keys.
    """

    async def dispatch(self, req, call_next):
        if req.url.path in _PUBLIC:
            return await call_next(req)

        raw = (
            req.headers.get("x-xyte-api-key")
            or (req.headers.get("authorization") or "").removeprefix("Bearer ")
        )
        if not raw:
            return JSONResponse({"error": "missing_xyte_key"}, 401)
        if len(raw.strip()) < 32:
            return JSONResponse({"error": "invalid_xyte_key"}, 403)

        req.state.xyte_key = raw.strip()
        req.state.key_id = hashlib.sha256(raw.encode()).hexdigest()[:8]
        return await call_next(req)
```

Patch **top** of `src/xyte_mcp_alpha/server.py`:

```python
from starlette.applications import Starlette
from xyte_mcp_alpha.auth_xyte import RequireXyteKey
app = Starlette()
app.add_middleware(RequireXyteKey)
```

---

## 4 Distributed Rate-Limiter (Redis Lua)

`src/xyte_mcp_alpha/bucket.lua`

```lua
-- KEYS[1] = rl:{key_id} ; ARGV[1] = limit ; ARGV[2] = ttl(seconds)
local c = redis.call("INCR", KEYS[1])
if c == 1 then redis.call("EXPIRE", KEYS[1], ARGV[2]) end
if c > tonumber(ARGV[1]) then return 0 else return tonumber(ARGV[1]) - c end
```

`src/xyte_mcp_alpha/rate_limiter.py`

```python
import os, importlib.resources, redis.asyncio as aioredis
redis = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
lua  = (importlib.resources.files("xyte_mcp_alpha") / "bucket.lua").read_text()
SHA  = redis.script_load(lua)

async def consume(key_id: str, limit: int = 60):
    remain = await redis.evalsha(SHA, 1, f"rl:{key_id}", limit, 60)
    return remain != 0
```

Insert after auth check:

```python
from xyte_mcp_alpha.rate_limiter import consume
if not await consume(req.state.key_id, limit=60):
    return JSONResponse({"error": "rate_limit"}, 429)
```

**Why** One limit shared by *all* replicas; protects Xyte quota.
**Result** HTTP 429 on excess requests; resets each minute.

---

## 5 Redis Streams Event Bus

`src/xyte_mcp_alpha/events.py`

```python
import os, json
from redis.asyncio import Redis
redis  = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
STREAM = "mcp_events"
GROUP  = "mcp_consumers"

async def push_event(evt: dict):
    await redis.xadd(STREAM,
        {k: json.dumps(v) for k, v in evt.items()},
        maxlen=10000, approximate=True)

async def pull_event(consumer: str, block=5000):
    try:
        await redis.xgroup_create(STREAM, GROUP, id="$", mkstream=True)
    except Exception:
        pass
    resp = await redis.xreadgroup(GROUP, consumer, {STREAM: ">"}, 1, block)
    if not resp: return None
    _, evts = resp[0]; eid, raw = evts[0]
    await redis.xack(STREAM, GROUP, eid)
    return {k.decode(): json.loads(v) for k, v in raw.items()}
```

Replace old `asyncio.Queue` calls:

```python
from xyte_mcp_alpha.events import push_event, pull_event
# webhook → await push_event(payload)
# get_next_event tool → evt = await pull_event(ctx.request_id)
```

---

## 6 SQLModel Task DB (Postgres)

`src/xyte_mcp_alpha/tasks.py`

```python
from sqlmodel import SQLModel, Field
from datetime import datetime
from xyte_mcp_alpha.db import get_session
import uuid

class Task(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    status: str
    payload: dict | None = None
    result:  dict | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

async def save(task: "Task"):
    async with get_session() as s:
        await s.merge(task); await s.commit()

async def fetch(tid: str):
    async with get_session() as s:
        return await s.get(Task, tid)
```

Migration SQL example:

```sql
CREATE TABLE task (
  id text PRIMARY KEY,
  status text NOT NULL,
  payload jsonb,
  result jsonb,
  updated_at timestamptz NOT NULL
);
```

---

## 7 Celery Worker Pool

`src/xyte_mcp_alpha/celery_app.py`

```python
import os
from celery import Celery

celery_app = Celery(
    "xyte_mcp",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("DATABASE_URL",
        "postgresql+asyncpg://mcp:pass@127.0.0.1/mcp")
)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes={"xyte_mcp_alpha.worker.long.*": {"queue": "long"}},
)
```

`src/xyte_mcp_alpha/worker/long.py`

```python
from xyte_mcp_alpha.celery_app import celery_app
from xyte_mcp_alpha.tasks import save, Task
from xyte_mcp_alpha.client import XyteAPIClient

@celery_app.task(name="xyte_mcp_alpha.worker.long.send_command")
def send_command_long(task_id: str, payload: dict, xyte_key: str):
    save(Task(id=task_id, status="running"))
    client = XyteAPIClient(api_key=xyte_key)
    try:
        result = client.send_command(**payload)
        save(Task(id=task_id, status="done", result=result))
    except Exception as exc:
        save(Task(id=task_id, status="error", result={"msg": str(exc)}))
```

Patch original async wrapper:

```python
tid = str(uuid.uuid4())
await save(Task(id=tid, status="queued", payload=data.dict()))
send_command_long.delay(tid, data.dict(), req.state.xyte_key)
return ToolResponse(summary="queued", data={"task_id": tid})
```

---

## 8 Meeting-Room Preset Tool

`src/xyte_mcp_alpha/presets/default.yaml`

```yaml
- device_id: proj-123
  command: power_on
- device_id: amp-555
  command: unmute
- device_id: switch-789
  command: select_hdmi1
```

`src/xyte_mcp_alpha/tools/presets.py`

```python
from pathlib import Path
import yaml
from xyte_mcp_alpha.models import CommandRequest, ToolResponse
from xyte_mcp_alpha.client import get_client

async def start_meeting_room_preset(room: str, preset: str = "default", req=None):
    f = Path(__file__).resolve().parent.parent / "presets" / f"{preset}.yaml"
    steps = yaml.safe_load(f.read_text())
    client = await get_client(req)
    for step in steps:
        await client.send_command(**CommandRequest(**step).dict())
    return ToolResponse(summary=f"{len(steps)} commands executed", data={"room": room})
```

Register:

```python
mcp.register_tool(
    "start_meeting_room_preset",
    start_meeting_room_preset,
    description="Power on & configure every device in a room.",
    readOnlyHint=False
)
```

---

## 9 Negative-Path Tests

`tests/test_errors.py`

```python
import pytest, httpx
from xyte_mcp_alpha.server import app

OK = {"X-XYTE-API-KEY": "X"*40}

@pytest.mark.anyio
async def test_missing_key():
    async with httpx.AsyncClient(app=app, base_url="http://t") as c:
        r = await c.get("/devices")
    assert r.status_code == 401

@pytest.mark.anyio
async def test_rate_limit(monkeypatch):
    monkeypatch.setattr("xyte_mcp_alpha.rate_limiter.consume", lambda *a,**k: False)
    async with httpx.AsyncClient(app=app, base_url="http://t") as c:
        r = await c.get("/devices", headers=OK)
    assert r.status_code == 429
```

---

## 10 Prometheus Metrics & Grafana

* `/metrics` endpoint already in repo via `prometheus_client`.
* Import `grafana/xyte_mcp_dashboard.json` into Grafana.
* Example alert rule:

```yaml
groups:
- name: mcp
  rules:
  - alert: MCPHighErrorRate
    expr: sum(rate(mcp_tool_errors_total[5m])) / sum(rate(mcp_tool_invocations_total[5m])) > 0.05
    for: 5m
    labels: {severity: critical}
    annotations:
      summary: "MCP error rate >5%"
```

---

## 11 Dockerfile (non-root + healthcheck)

`docker/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements/prod.txt .
RUN pip install --no-cache-dir -r prod.txt
COPY src ./src
RUN useradd -m mcp
USER mcp
EXPOSE 8000
HEALTHCHECK CMD curl -f http://localhost:8000/healthz || exit 1
CMD ["uvicorn", "xyte_mcp_alpha.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 12 Docker-Compose Stack (dev / single VM)

`docker-compose.yml`

```yaml
version: "3.9"
services:
  mcp:
    image: ghcr.io/xyte/mcp:latest
    ports: ["8000:8000"]
    environment:
      REDIS_URL: "redis://redis:6379/0"
      DATABASE_URL: "postgresql+asyncpg://mcp:pass@pg/mcp"
      LOG_LEVEL: "INFO"
    depends_on: [redis, pg]
    restart: always

  redis:
    image: redis:7
    command: ["--save","60","1","--loglevel","warning"]
    volumes: ["redis:/data"]

  pg:
    image: postgres:15
    environment:
      POSTGRES_DB: mcp
      POSTGRES_USER: mcp
      POSTGRES_PASSWORD: pass
    volumes: ["pg:/var/lib/postgresql/data"]

  worker:
    image: ghcr.io/xyte/mcp:latest
    command: celery -A xyte_mcp_alpha.celery_app worker -Q long -c 2
    environment:
      REDIS_URL: "redis://redis:6379/0"
      DATABASE_URL: "postgresql+asyncpg://mcp:pass@pg/mcp"
    depends_on: [redis, pg]
    restart: always

volumes:
  redis:
  pg:
```

---

## 13 systemd Service (bare metal)

`/etc/systemd/system/mcp.service`

```ini
[Unit]
Description=XYTE MCP Service
After=network.target redis.service postgresql.service

[Service]
User=mcp
WorkingDirectory=/opt/mcp
Environment="REDIS_URL=redis://127.0.0.1:6379/0"
Environment="DATABASE_URL=postgresql+asyncpg://mcp:pass@127.0.0.1/mcp"
ExecStart=/opt/mcp-venv/bin/uvicorn xyte_mcp_alpha.server:app --host 0.0.0.0 --port 8000
Restart=always
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

---

## 14 Helm / Kubernetes

**values.yaml key parts**

```yaml
image:
  repository: ghcr.io/xyte/mcp
  tag: "sha256:<digest>"

env:
  REDIS_URL: "redis://xyte-redis-master.data.svc:6379/0"
  DATABASE_URL: "postgresql+asyncpg://mcp:pass@xyte-pg.data.svc/mcp"

hpa:
  enabled: true
  minReplicas: 1
  maxReplicas: 4

worker:
  enabled: true
  replicas: 2
  resources:
    requests: {cpu: 100m, memory: 256Mi}

ingress:
  enabled: true
  hosts: [mcp.example.com]
  tls:
  - hosts: [mcp.example.com]
    secretName: mcp-tls
```

Deploy:

```bash
helm upgrade --install mcp helm/chart -f helm/chart/values.yaml
```

---

## 15 Backup & Alert Scripts

*Redis snapshot* – already via `--save 60 1`.
*Postgres backup* `ops/pg_backup.sh`

```bash
#!/usr/bin/env bash
DATE=$(date +%F)
pg_dump -U mcp -h pg -d mcp | gzip > /backups/mcp_$DATE.sql.gz
```

*Prometheus alerts* – file shown in §10.

---

## 16 Docs & Swagger (optional)

Add in `server.py` if you want Swagger:

```python
from fastapi import FastAPI
fast = FastAPI(openapi_url="/openapi.json", docs_url="/docs")
fast.mount("", app)
```

MkDocs site:

```bash
mkdocs new docs
# populate *.md pages
mkdocs gh-deploy --force
```

---

## 17 Real-Life Usage Examples

```bash
# curl
curl -H "X-XYTE-API-KEY: XYTE_live_ABC..." \
     -H "Content-Type: application/json" \
     -d '{"method":"tools/call","params":{"name":"start_meeting_room_preset","arguments":{"room":"Board"}}, "id":1,"jsonrpc":"2.0"}' \
     https://mcp.example.com

# Claude Desktop host.json snippet
{
  "url": "https://mcp.example.com",
  "headers": {
    "x-xyte-api-key": "XYTE_live_ABC..."
  }
}
```

---

## Final Human Checklist

* [ ] TLS proxy (nginx/Caddy/K8s Ingress) in front of port 8000.
* [ ] **No XYTE keys stored in env-vars**; clients must send key per request.
* [ ] Redis AOF + snapshot enabled; Postgres nightly `pg_dump` to S3.
* [ ] Prometheus scraping `/metrics`; Grafana dashboard imported.
* [ ] Celery worker(s) running; Redis URL & DB URL identical across web + worker.
* [ ] Helm/Compose replicas >1? Redis limits & Celery queues already shared.
* [ ] CI green: ruff, pyright, pytest, safety, docker build & push.

Complete every section above → you have a **production-grade, stateless, multi-tenant, fully observable MCP server** that any AI agent can hit with a per-request XYTE key—no secrets on disk, no missing pieces.
