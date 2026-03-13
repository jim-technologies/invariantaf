"""Shared fixtures for Alternative.me MCP integration tests."""

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

FEAR_GREED_ENTRY = {
    "value": "25",
    "value_classification": "Extreme Fear",
    "timestamp": "1710288000",
    "time_until_update": "43210",
}

COIN_TICKER_1 = {
    "id": 1,
    "name": "Bitcoin",
    "symbol": "BTC",
    "rank": 1,
    "last_updated": 1710288000,
    "quotes": {
        "USD": {
            "price": 65000.50,
            "market_cap": 1270000000000,
            "volume_24h": 35000000000,
            "percentage_change_1h": 0.25,
            "percentage_change_24h": 2.10,
            "percentage_change_7d": 5.50,
        },
    },
}

COIN_TICKER_2 = {
    "id": 1027,
    "name": "Ethereum",
    "symbol": "ETH",
    "rank": 2,
    "last_updated": 1710288000,
    "quotes": {
        "USD": {
            "price": 3500.75,
            "market_cap": 420000000000,
            "volume_24h": 18000000000,
            "percentage_change_1h": -0.15,
            "percentage_change_24h": 1.80,
            "percentage_change_7d": 3.20,
        },
    },
}

LISTING_1 = {
    "id": 1,
    "name": "Bitcoin",
    "symbol": "BTC",
    "website_slug": "bitcoin",
    "rank": 1,
}

LISTING_2 = {
    "id": 1027,
    "name": "Ethereum",
    "symbol": "ETH",
    "website_slug": "ethereum",
    "rank": 2,
}


class _AlternativeMeHandler(BaseHTTPRequestHandler):
    """Mock Alternative.me API backend for integration tests."""

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path.rstrip("/")
        query = self._parse_query()

        if path == "/fng":
            limit = int(query.get("limit", "1"))
            entries = [FEAR_GREED_ENTRY] * limit
            self._write_json(200, {"name": "Fear and Greed Index", "data": entries})
            return

        if path == "/v2/ticker":
            self._write_json(200, {
                "data": {"1": COIN_TICKER_1, "1027": COIN_TICKER_2},
            })
            return

        # /v2/ticker/<id>
        parts = path.split("/")
        if len(parts) == 4 and parts[1] == "v2" and parts[2] == "ticker":
            coin_id = parts[3]
            ticker = COIN_TICKER_1 if coin_id == "1" else COIN_TICKER_2
            self._write_json(200, {"data": {coin_id: ticker}})
            return

        if path == "/v2/listings":
            self._write_json(200, {"data": [LISTING_1, LISTING_2]})
            return

        self.send_response(404)
        self.end_headers()

    def _parse_query(self) -> dict[str, str]:
        if "?" not in self.path:
            return {}
        qs = self.path.split("?", 1)[1]
        params = urllib.parse.parse_qs(qs)
        return {k: v[0] for k, v in params.items()}

    def _write_json(self, status: int, payload: object):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format, *args):  # noqa: A003
        pass


@pytest.fixture
def backend_url():
    httpd = ThreadingHTTPServer(("localhost", 0), _AlternativeMeHandler)
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
    from alternativeme_mcp.gen.alternativeme.v1 import alternativeme_pb2 as _alternativeme_pb2  # noqa: F401
    from alternativeme_mcp.service import AlternativeMeService

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-alternativeme", version="0.0.1")
    servicer = AlternativeMeService(base_url=backend_url)
    srv.register(servicer, service_name="alternativeme.v1.AlternativeMeService")
    yield srv
    srv.stop()
