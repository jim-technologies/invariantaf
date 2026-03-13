"""Shared fixtures for Gate.io MCP integration tests."""

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
    "currency_pair": "BTC_USDT",
    "last": "64500.5",
    "lowest_ask": "64510.0",
    "lowest_size": "0.5",
    "highest_bid": "64500.0",
    "highest_size": "1.2",
    "change_percentage": "2.5",
    "base_volume": "12000.123",
    "quote_volume": "774000000.5",
    "high_24h": "65000.0",
    "low_24h": "63500.0",
}

SPOT_ORDERBOOK = {
    "current": 1772720841000,
    "update": 1772720841000,
    "asks": [
        ["64510.0", "3.0"],
        ["64520.0", "7.0"],
    ],
    "bids": [
        ["64500.0", "5.0"],
        ["64490.0", "10.0"],
    ],
}

# Gate.io candlestick format: [timestamp, quote_vol, close, high, low, open, base_vol, is_closed]
CANDLESTICKS = [
    ["1772720000", "500000.0", "64500.0", "65000.0", "63900.0", "64000.0", "100.5", "true"],
    ["1772723600", "600000.0", "64300.0", "64800.0", "64100.0", "64500.0", "120.3", "true"],
    ["1772727200", "400000.0", "64400.0", "64500.0", "64200.0", "64300.0", "80.1", "false"],
]

CURRENCY_PAIR = {
    "id": "BTC_USDT",
    "base": "BTC",
    "quote": "USDT",
    "fee": "0.2",
    "min_base_amount": "0.0001",
    "min_quote_amount": "1",
    "amount_precision": 4,
    "precision": 2,
    "trade_status": "tradable",
}

FUTURES_TICKER = {
    "contract": "BTC_USDT",
    "last": "64500.5",
    "change_percentage": "2.5",
    "volume_24h": "50000",
    "volume_24h_base": "12000.0",
    "volume_24h_quote": "774000000.5",
    "mark_price": "64502.5",
    "index_price": "64500.0",
    "funding_rate": "0.00015",
    "funding_rate_indicative": "0.0001",
    "highest_bid": "64500.0",
    "lowest_ask": "64510.0",
    "high_24h": "65000.0",
    "low_24h": "63500.0",
    "total_size": "250000",
}

FUTURES_ORDERBOOK = {
    "current": 1772720841000,
    "update": 1772720841000,
    "asks": [
        {"p": "64510.0", "s": 300},
        {"p": "64520.0", "s": 700},
    ],
    "bids": [
        {"p": "64500.0", "s": 500},
        {"p": "64490.0", "s": 1000},
    ],
}


class _GateioHandler(BaseHTTPRequestHandler):
    """Mock Gate.io API backend for integration tests."""

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        query = self._parse_query()

        if path == "/api/v4/spot/tickers":
            self._write_json(200, [SPOT_TICKER])
            return

        if path == "/api/v4/spot/order_book":
            self._write_json(200, SPOT_ORDERBOOK)
            return

        if path == "/api/v4/spot/candlesticks":
            self._write_json(200, CANDLESTICKS)
            return

        if path == "/api/v4/spot/currency_pairs":
            self._write_json(200, [CURRENCY_PAIR])
            return

        if path == "/api/v4/futures/usdt/tickers":
            self._write_json(200, [FUTURES_TICKER])
            return

        if path == "/api/v4/futures/usdt/order_book":
            self._write_json(200, FUTURES_ORDERBOOK)
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
    httpd = ThreadingHTTPServer(("localhost", 0), _GateioHandler)
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
    from gateio_mcp.gen.gateio.v1 import gateio_pb2 as _gateio_pb2  # noqa: F401
    from gateio_mcp.service import GateioService

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-gateio", version="0.0.1")
    servicer = GateioService(base_url=backend_url)
    srv.register(servicer, service_name="gateio.v1.GateioService")
    yield srv
    srv.stop()
