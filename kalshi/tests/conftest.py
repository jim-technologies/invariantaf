"""Shared fixtures for Kalshi MCP tests."""

from __future__ import annotations

import json
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")


class _BackendHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/exchange/status":
            self._write_data({"exchange_active": True, "maintenance_start_time": ""})
            return

        if path.startswith("/historical/markets/"):
            ticker = path.split("/")[-1]
            self._write_data({"market": {"ticker": ticker, "status": "settled"}})
            return

        if path == "/markets":
            limit = int((query.get("limit") or ["2"])[0])
            self._write_data(
                {
                    "markets": [{"ticker": "TEST-1"}, {"ticker": "TEST-2"}][:limit],
                    "cursor": "",
                }
            )
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path

        if path == "/portfolio/orders":
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode() or "{}")
            self._write_data({"order": {"status": "accepted", "echo": payload}})
            return

        self.send_response(404)
        self.end_headers()

    def _write_data(self, payload: object):
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format, *args):
        pass


@pytest.fixture
def backend_url():
    httpd = ThreadingHTTPServer(("localhost", 0), _BackendHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://localhost:{port}"
    finally:
        httpd.shutdown()


@pytest.fixture
def server(backend_url: str):
    from invariant import Server
    from gen.kalshi.v1 import kalshi_pb2 as _kalshi_pb2  # noqa: F401

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-kalshi", version="0.0.1")
    srv.connect_http(backend_url, service_name="kalshi.v1.KalshiService")
    yield srv
    srv.stop()
