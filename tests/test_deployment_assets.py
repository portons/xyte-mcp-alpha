import os
import importlib
import yaml
import httpx
import pytest

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_pg_backup_script_exists():
    path = os.path.join('ops', 'pg_backup.sh')
    assert os.path.isfile(path)
    with open(path, 'r') as f:
        first = f.readline().strip()
    assert first == '#!/usr/bin/env bash'


def test_prometheus_alerts_exists():
    assert os.path.isfile(os.path.join('prometheus', 'alerts.yaml'))


def test_real_life_examples_doc():
    assert os.path.isfile(os.path.join('docs', 'REAL_LIFE_USAGE.md'))


def test_helm_values_keys():
    with open('helm/values.yaml') as f:
        values = yaml.safe_load(f)
    assert 'worker' in values
    assert 'hpa' in values
    assert 'ingress' in values
    assert 'REDIS_URL' in values['env']
    assert 'DATABASE_URL' in values['env']


@pytest.mark.anyio
async def test_swagger_docs(monkeypatch):
    if importlib.util.find_spec("fastapi") is None:
        pytest.skip("fastapi not installed")
    monkeypatch.setenv('XYTE_ENABLE_SWAGGER', '1')
    import xyte_mcp.server as server
    importlib.reload(server)
    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url='http://t') as c:
        r = await c.get('/docs')
    assert r.status_code == 200
