"""Shared fixtures for Bitget MCP integration tests."""

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

SPOT_TICKER = {
    "symbol": "BTCUSDT",
    "high24h": "65000.00",
    "open": "64000.00",
    "lastPr": "64500.00",
    "low24h": "63500.00",
    "quoteVolume": "500000000.00",
    "baseVolume": "7800.50",
    "usdVolume": "500000000.00",
    "bidPr": "64490.00",
    "askPr": "64510.00",
    "bidSz": "1.5",
    "askSz": "2.0",
    "openUtc": "64100.00",
    "ts": "1772720841000",
    "changeUtc24h": "0.0062",
    "change24h": "0.0078",
}

SPOT_ORDERBOOK = {
    "asks": [["64510.00", "2.0"], ["64520.00", "5.0"]],
    "bids": [["64490.00", "1.5"], ["64480.00", "3.0"]],
    "ts": "1772720841000",
}

SPOT_CANDLES = [
    ["1772720000000", "64000.00", "64600.00", "63900.00", "64500.00", "1000.0", "64000000.0", "64000000.0"],
    ["1772723600000", "64500.00", "64800.00", "64200.00", "64300.00", "1200.0", "77000000.0", "77000000.0"],
    ["1772727200000", "64300.00", "64500.00", "64100.00", "64400.00", "800.0", "51500000.0", "51500000.0"],
]

FUTURES_TICKER = {
    "symbol": "BTCUSDT",
    "lastPr": "64500.00",
    "bidPr": "64490.00",
    "askPr": "64510.00",
    "bidSz": "10.0",
    "askSz": "8.0",
    "high24h": "65000.00",
    "low24h": "63500.00",
    "timestamp": "1772720841000",
    "priceChangePercent24h": "0.0078",
    "baseVolume": "50000.0",
    "quoteVolume": "3200000000.00",
    "usdVolume": "3200000000.00",
    "openUtc": "64100.00",
    "changeUtc24h": "0.0062",
    "indexPrice": "64495.00",
    "fundingRate": "0.0001",
    "holdVolume": "120000.0",
    "open24h": "64000.00",
}

FUTURES_ORDERBOOK = {
    "asks": [["64510.00", "8.0"], ["64520.00", "12.0"]],
    "bids": [["64490.00", "10.0"], ["64480.00", "15.0"]],
    "ts": "1772720841000",
}


class _BitgetHandler(BaseHTTPRequestHandler):
    """Mock Bitget API backend for integration tests."""

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        query = self._parse_query()

        if path == "/api/v2/spot/market/tickers":
            self._write_data([SPOT_TICKER])
            return

        if path == "/api/v2/spot/market/orderbook":
            self._write_data(SPOT_ORDERBOOK)
            return

        if path == "/api/v2/spot/market/candles":
            self._write_data(SPOT_CANDLES)
            return

        if path == "/api/v2/mix/market/tickers":
            self._write_data([FUTURES_TICKER])
            return

        if path == "/api/v2/mix/market/merge-depth":
            self._write_data(FUTURES_ORDERBOOK)
            return

        self.send_response(404)
        self.end_headers()

    def _parse_query(self) -> dict[str, str]:
        if "?" not in self.path:
            return {}
        qs = self.path.split("?", 1)[1]
        params = urllib.parse.parse_qs(qs)
        return {k: v[0] for k, v in params.items()}

    def _write_data(self, data: object):
        """Write a Bitget-style envelope response."""
        payload = {"code": "00000", "msg": "success", "data": data}
        self._write_json(200, payload)

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
    httpd = ThreadingHTTPServer(("localhost", 0), _BitgetHandler)
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
    from bitget_mcp.gen.bitget.v1 import bitget_pb2 as _bitget_pb2  # noqa: F401
    from bitget_mcp.service import BitgetService

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-bitget", version="0.0.1")
    servicer = BitgetService(base_url=backend_url)
    srv.register(servicer, service_name="bitget.v1.BitgetService")
    yield srv
    srv.stop()
