import io
import logging
import os
import importlib
import unittest
from starlette.testclient import TestClient

os.environ.setdefault("XYTE_API_KEY", "test")
from xyte_mcp import http as http_mod

class LogRedactionTestCase(unittest.TestCase):
    def setUp(self):
        importlib.reload(http_mod)
        self.client = TestClient(http_mod.app)
        self.stream = io.StringIO()
        handler = logging.StreamHandler(self.stream)
        logger = logging.getLogger("xyte_mcp")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        self.handler = handler

    def tearDown(self):
        logging.getLogger("xyte_mcp").removeHandler(self.handler)

    def test_header_redacted(self):
        self.client.get("/v1/healthz", headers={"Authorization": "SECRETKEY"})
        out = self.stream.getvalue()
        assert "****" in out
        assert "SECRETKEY" not in out

