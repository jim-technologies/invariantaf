"""Shared fixtures for Manifold Markets MCP proxy tests."""

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

POOL = {"YES": 1200.0, "NO": 800.0}

MARKET = {
    "id": "mkt-abc123",
    "question": "Will AI pass the Turing test by 2030?",
    "url": "https://manifold.markets/user/will-ai-pass-turing-test",
    "creatorId": "user-creator-1",
    "creatorUsername": "forecaster42",
    "createdTime": 1700000000000,
    "closeTime": 1900000000000,
    "mechanism": "cpmm-1",
    "outcomeType": "BINARY",
    "probability": 0.65,
    "pool": POOL,
    "volume": 50000.0,
    "volume24Hours": 1200.0,
    "totalLiquidity": 8000.0,
    "isResolved": False,
    "resolution": "",
    "uniqueBettorCount": 42,
    "lastBetTime": 1700100000000,
    "lastCommentTime": 1700090000000,
    "descriptionText": "Resolves YES if a generally accepted Turing test is passed.",
}

MARKET_2 = {
    **MARKET,
    "id": "mkt-def456",
    "question": "Will humans land on Mars by 2035?",
    "url": "https://manifold.markets/user/mars-landing",
    "probability": 0.30,
    "volume": 25000.0,
}

POSITION = {
    "hasYesShares": True,
    "hasNoShares": False,
    "yesShares": 150.0,
    "noShares": 0.0,
    "profit": 42.5,
    "userId": "user-pos-1",
    "userName": "bettor99",
}

USER = {
    "id": "user-abc",
    "name": "Alice Forecaster",
    "username": "aliceforecaster",
    "avatarUrl": "https://manifold.markets/avatar/alice.png",
    "balance": 1500.0,
    "totalDeposits": 1000.0,
    "profit": 500.0,
}


class _ManifoldHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # GET /markets
        if path == "/markets":
            limit = int(query.get("limit", ["10"])[0])
            markets = [MARKET, MARKET_2][:limit]
            self._write_json(200, markets)
            return

        # GET /market/{marketId}/positions
        if path.startswith("/market/") and path.endswith("/positions"):
            parts = path.split("/")
            # /market/{id}/positions -> parts = ['', 'market', '{id}', 'positions']
            if len(parts) == 4:
                self._write_json(200, [POSITION])
                return

        # GET /market/{marketId}
        if path.startswith("/market/"):
            parts = path.split("/")
            if len(parts) == 3:
                market_id = parts[2]
                if market_id == MARKET["id"]:
                    self._write_json(200, MARKET)
                elif market_id == MARKET_2["id"]:
                    self._write_json(200, MARKET_2)
                else:
                    self._write_json(404, {"error": "Market not found"})
                return

        # GET /slug/{slug}
        if path.startswith("/slug/"):
            self._write_json(200, MARKET)
            return

        # GET /search-markets
        if path == "/search-markets":
            self._write_json(200, [MARKET])
            return

        # GET /user/by-username/{username}
        if path.startswith("/user/by-username/"):
            self._write_json(200, USER)
            return

        # GET /user/{userId}
        if path.startswith("/user/"):
            parts = path.split("/")
            if len(parts) == 3:
                self._write_json(200, USER)
                return

        self.send_response(404)
        self.end_headers()

    def _write_json(self, status: int, payload: object):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format, *args):  # noqa: A003
        pass


def _run_backend(handler_cls):
    httpd = ThreadingHTTPServer(("localhost", 0), handler_cls)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, f"http://localhost:{port}"


@pytest.fixture
def manifold_url():
    httpd, url = _run_backend(_ManifoldHandler)
    try:
        yield url
    finally:
        httpd.shutdown()


@pytest.fixture
def server(manifold_url: str):
    from invariant import Server
    from gen.manifold.v1 import manifold_pb2 as _manifold_pb2  # noqa: F401

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-manifold", version="0.0.1")
    srv.connect_http(manifold_url, service_name="manifold.v1.ManifoldService")
    yield srv
    srv.stop()
