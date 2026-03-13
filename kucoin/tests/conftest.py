"""Shared fixtures for KuCoin MCP integration tests."""

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

ALL_TICKERS_DATA = {
    "time": 1710300000000,
    "ticker": [
        {
            "symbol": "BTC-USDT",
            "symbolName": "BTC-USDT",
            "buy": "83500.1",
            "sell": "83500.2",
            "bestBidSize": "0.5",
            "bestAskSize": "0.3",
            "changeRate": "0.025",
            "changePrice": "2050.5",
            "high": "84000",
            "low": "81000",
            "vol": "12500.5",
            "volValue": "1043791750",
            "last": "83500.15",
            "averagePrice": "82500",
            "takerFeeRate": "0.001",
            "makerFeeRate": "0.001",
            "takerCoefficient": "1",
            "makerCoefficient": "1",
        },
        {
            "symbol": "ETH-USDT",
            "symbolName": "ETH-USDT",
            "buy": "1920.5",
            "sell": "1920.8",
            "bestBidSize": "5.0",
            "bestAskSize": "3.2",
            "changeRate": "0.015",
            "changePrice": "28.5",
            "high": "1950",
            "low": "1890",
            "vol": "85000.2",
            "volValue": "163200384",
            "last": "1920.65",
            "averagePrice": "1910",
            "takerFeeRate": "0.001",
            "makerFeeRate": "0.001",
            "takerCoefficient": "1",
            "makerCoefficient": "1",
        },
    ],
}

TICKER_STATS = {
    "time": "1710300000000",
    "symbol": "BTC-USDT",
    "buy": "83500.1",
    "sell": "83500.2",
    "changeRate": "0.025",
    "changePrice": "2050.5",
    "high": "84000",
    "low": "81000",
    "vol": "12500.5",
    "volValue": "1043791750",
    "last": "83500.15",
    "averagePrice": "82500",
    "takerFeeRate": "0.001",
    "makerFeeRate": "0.001",
    "takerCoefficient": "1",
    "makerCoefficient": "1",
}

ORDERBOOK = {
    "sequence": "1234567890",
    "time": 1710300000000,
    "bids": [["83500.1", "0.5"], ["83499.5", "1.2"]],
    "asks": [["83500.2", "0.3"], ["83500.8", "0.8"]],
}

KLINES = [
    ["1710296400", "83000", "83500", "83600", "82900", "500.5", "41525000"],
    ["1710300000", "83500", "83200", "83700", "83100", "450.2", "37539200"],
    ["1710303600", "83200", "83400", "83500", "83000", "380.1", "31652340"],
]

SYMBOLS = [
    {
        "symbol": "BTC-USDT",
        "name": "BTC-USDT",
        "baseCurrency": "BTC",
        "quoteCurrency": "USDT",
        "feeCurrency": "USDT",
        "market": "USDS",
        "baseMinSize": "0.00001",
        "quoteMinSize": "0.1",
        "baseMaxSize": "10000",
        "quoteMaxSize": "99999999",
        "baseIncrement": "0.00000001",
        "quoteIncrement": "0.000001",
        "priceIncrement": "0.1",
        "priceLimitRate": "0.1",
        "minFunds": "0.1",
        "isMarginEnabled": True,
        "enableTrading": True,
    },
    {
        "symbol": "ETH-USDT",
        "name": "ETH-USDT",
        "baseCurrency": "ETH",
        "quoteCurrency": "USDT",
        "feeCurrency": "USDT",
        "market": "USDS",
        "baseMinSize": "0.0001",
        "quoteMinSize": "0.1",
        "baseMaxSize": "10000",
        "quoteMaxSize": "99999999",
        "baseIncrement": "0.0000001",
        "quoteIncrement": "0.000001",
        "priceIncrement": "0.01",
        "priceLimitRate": "0.1",
        "minFunds": "0.1",
        "isMarginEnabled": True,
        "enableTrading": True,
    },
]

FIAT_PRICES = {
    "BTC": "83500.15",
    "ETH": "1920.65",
    "SOL": "135.20",
}


class _KucoinHandler(BaseHTTPRequestHandler):
    """Mock KuCoin API backend for integration tests."""

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        query = self._parse_query()

        if path == "/api/v1/market/allTickers":
            self._write_data(ALL_TICKERS_DATA)
            return

        if path == "/api/v1/market/stats":
            self._write_data(TICKER_STATS)
            return

        if path == "/api/v1/market/orderbook/level2_20":
            self._write_data(ORDERBOOK)
            return

        if path == "/api/v1/market/candles":
            self._write_data(KLINES)
            return

        if path == "/api/v2/symbols":
            self._write_data(SYMBOLS)
            return

        if path == "/api/v1/prices":
            self._write_data(FIAT_PRICES)
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
        """Write a KuCoin-style response with envelope."""
        payload = {"code": "200000", "data": data}
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
    httpd = ThreadingHTTPServer(("localhost", 0), _KucoinHandler)
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
    from kucoin_mcp.gen.kucoin.v1 import kucoin_pb2 as _kucoin_pb2  # noqa: F401
    from kucoin_mcp.service import KucoinService

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-kucoin", version="0.0.1")
    servicer = KucoinService(base_url=backend_url)
    srv.register(servicer, service_name="kucoin.v1.KucoinService")
    yield srv
    srv.stop()
