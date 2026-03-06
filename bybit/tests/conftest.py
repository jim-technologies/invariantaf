"""Shared fixtures for Bybit MCP tests."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")
TEST_API_KEY = "test-api-key"
TEST_API_SECRET = "test-api-secret"
TEST_RECV_WINDOW = "5000"


class _BackendHandler(BaseHTTPRequestHandler):
    def _write_json(self, payload: object, *, status: int = 200):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _auth_error(self, message: str):
        self._write_json({"retCode": 10001, "retMsg": message, "result": {}, "retExtInfo": {}, "time": 0}, status=401)

    def _verify_private(self, query: str, body_text: str):
        api_key = self.headers.get("X-BAPI-API-KEY")
        timestamp = self.headers.get("X-BAPI-TIMESTAMP")
        recv_window = self.headers.get("X-BAPI-RECV-WINDOW")
        signature = self.headers.get("X-BAPI-SIGN")
        sign_type = self.headers.get("X-BAPI-SIGN-TYPE")

        if api_key != TEST_API_KEY:
            raise ValueError("missing or invalid X-BAPI-API-KEY")
        if not timestamp or not timestamp.isdigit():
            raise ValueError("missing or invalid X-BAPI-TIMESTAMP")
        if recv_window != TEST_RECV_WINDOW:
            raise ValueError("missing or invalid X-BAPI-RECV-WINDOW")
        if sign_type != "2":
            raise ValueError("missing or invalid X-BAPI-SIGN-TYPE")

        payload = query if self.command == "GET" else body_text
        expected = hmac.new(
            TEST_API_SECRET.encode(),
            f"{timestamp}{TEST_API_KEY}{recv_window}{payload}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if signature != expected:
            raise ValueError("invalid X-BAPI-SIGN")

    def _ok(self, result: object):
        self._write_json(
            {
                "retCode": 0,
                "retMsg": "OK",
                "result": result,
                "retExtInfo": {},
                "time": 1700000000000,
            }
        )

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/v5/market/time":
            self._ok({"timeSecond": "1700000000", "timeNano": "1700000000000000000"})
            return

        if path == "/v5/account/wallet-balance":
            try:
                self._verify_private(parsed.query, "")
            except ValueError as exc:
                self._auth_error(str(exc))
                return

            self._ok(
                {
                    "accountType": (query.get("accountType") or [""])[0],
                    "list": [{"coin": [{"coin": "USDT", "walletBalance": "1000"}]}],
                }
            )
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        body_raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        body_text = body_raw.decode() if body_raw else ""

        if path == "/v5/order/create":
            try:
                self._verify_private(parsed.query, body_text)
            except ValueError as exc:
                self._auth_error(str(exc))
                return

            payload = json.loads(body_text or "{}")
            self._ok({"orderId": "order-123", "echo": payload})
            return

        self.send_response(404)
        self.end_headers()

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
def server(backend_url: str, monkeypatch: pytest.MonkeyPatch):
    from invariant import Server
    from gen.bybit.v1 import bybit_pb2 as _bybit_pb2  # noqa: F401

    from bybit_mcp.spec_meta import SERVICE_NAMES
    from main import _build_bybit_header_provider

    monkeypatch.setenv("BYBIT_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("BYBIT_API_SECRET", TEST_API_SECRET)
    monkeypatch.setenv("BYBIT_RECV_WINDOW", TEST_RECV_WINDOW)
    monkeypatch.setenv("BYBIT_SIGN_TYPE", "2")
    os.environ.pop("BYBIT_REFERER", None)

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-bybit", version="0.0.1")
    srv.use_http_header_provider(_build_bybit_header_provider(TEST_RECV_WINDOW))
    for service_name in SERVICE_NAMES:
        srv.connect_http(backend_url, service_name=service_name)

    yield srv
    srv.stop()
