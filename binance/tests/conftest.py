"""Shared fixtures for Binance MCP integration tests."""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")


class _BinanceHandler(BaseHTTPRequestHandler):
    """Mock Binance API backend for integration tests."""

    def do_GET(self):
        path = self.path.split("?")[0]
        query = self._parse_query()

        if path == "/api/v3/ticker/price":
            symbol = query.get("symbol")
            if symbol:
                self._write_json(200, {"symbol": symbol, "price": "50000.00"})
            else:
                self._write_json(
                    200,
                    [
                        {"symbol": "BTCUSDT", "price": "50000.00"},
                        {"symbol": "ETHUSDT", "price": "3000.00"},
                    ],
                )
            return

        if path == "/api/v3/ticker/24hr":
            symbol = query.get("symbol")
            ticker = {
                "symbol": symbol or "BTCUSDT",
                "priceChange": "100.00",
                "priceChangePercent": "0.20",
                "weightedAvgPrice": "49950.00",
                "prevClosePrice": "49900.00",
                "lastPrice": "50000.00",
                "lastQty": "0.01",
                "bidPrice": "49999.00",
                "bidQty": "1.5",
                "askPrice": "50001.00",
                "askQty": "2.0",
                "openPrice": "49900.00",
                "highPrice": "50500.00",
                "lowPrice": "49500.00",
                "volume": "1000.00",
                "quoteVolume": "50000000.00",
                "openTime": 1700000000000,
                "closeTime": 1700086400000,
                "firstId": 1,
                "lastId": 1000,
                "count": 1000,
            }
            if symbol:
                self._write_json(200, ticker)
            else:
                self._write_json(200, [ticker])
            return

        if path == "/api/v3/depth":
            self._write_json(
                200,
                {
                    "lastUpdateId": 123456,
                    "bids": [["49999.00", "1.5"], ["49998.00", "2.0"]],
                    "asks": [["50001.00", "1.0"], ["50002.00", "3.0"]],
                },
            )
            return

        if path == "/api/v3/klines":
            self._write_json(
                200,
                [
                    [
                        1700000000000,
                        "49900.00",
                        "50500.00",
                        "49500.00",
                        "50000.00",
                        "1000.00",
                        1700003600000,
                        "50000000.00",
                        500,
                        "600.00",
                        "30000000.00",
                        "0",
                    ],
                    [
                        1700003600000,
                        "50000.00",
                        "50200.00",
                        "49800.00",
                        "50100.00",
                        "800.00",
                        1700007200000,
                        "40000000.00",
                        400,
                        "500.00",
                        "25000000.00",
                        "0",
                    ],
                ],
            )
            return

        if path == "/api/v3/trades":
            self._write_json(
                200,
                [
                    {
                        "id": 1,
                        "price": "50000.00",
                        "qty": "0.1",
                        "quoteQty": "5000.00",
                        "time": 1700000000000,
                        "isBuyerMaker": False,
                        "isBestMatch": True,
                    },
                    {
                        "id": 2,
                        "price": "49999.00",
                        "qty": "0.2",
                        "quoteQty": "9999.80",
                        "time": 1700000001000,
                        "isBuyerMaker": True,
                        "isBestMatch": True,
                    },
                ],
            )
            return

        if path == "/api/v3/exchangeInfo":
            self._write_json(
                200,
                {
                    "timezone": "UTC",
                    "serverTime": 1700000000000,
                    "rateLimits": [
                        {
                            "rateLimitType": "REQUEST_WEIGHT",
                            "interval": "MINUTE",
                            "intervalNum": 1,
                            "limit": 6000,
                        }
                    ],
                    "symbols": [
                        {
                            "symbol": "BTCUSDT",
                            "status": "TRADING",
                            "baseAsset": "BTC",
                            "baseAssetPrecision": 8,
                            "quoteAsset": "USDT",
                            "quotePrecision": 8,
                            "orderTypes": ["LIMIT", "MARKET"],
                            "icebergAllowed": True,
                            "ocoAllowed": True,
                            "isSpotTradingAllowed": True,
                            "isMarginTradingAllowed": True,
                            "filters": [
                                {
                                    "filterType": "PRICE_FILTER",
                                    "minPrice": "0.01",
                                    "maxPrice": "1000000.00",
                                    "tickSize": "0.01",
                                },
                                {
                                    "filterType": "LOT_SIZE",
                                    "minQty": "0.00001",
                                    "maxQty": "9000.00",
                                    "stepSize": "0.00001",
                                },
                            ],
                            "permissions": ["SPOT", "MARGIN"],
                        }
                    ],
                },
            )
            return

        if path == "/api/v3/avgPrice":
            self._write_json(
                200,
                {"mins": 5, "price": "50000.00", "closeTime": 1700000000000},
            )
            return

        if path == "/api/v3/ticker/bookTicker":
            symbol = query.get("symbol")
            ticker = {
                "symbol": symbol or "BTCUSDT",
                "bidPrice": "49999.00",
                "bidQty": "1.5",
                "askPrice": "50001.00",
                "askQty": "2.0",
            }
            if symbol:
                self._write_json(200, ticker)
            else:
                self._write_json(200, [ticker])
            return

        self.send_response(404)
        self.end_headers()

    def _parse_query(self) -> dict[str, str]:
        if "?" not in self.path:
            return {}
        qs = self.path.split("?", 1)[1]
        import urllib.parse

        params = urllib.parse.parse_qs(qs)
        return {k: v[0] for k, v in params.items()}

    def _write_json(self, status: int, payload):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format, *args):
        pass


@pytest.fixture
def backend_url():
    httpd = ThreadingHTTPServer(("localhost", 0), _BinanceHandler)
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
    from binance_mcp.gen.binance.v1 import binance_pb2 as _binance_pb2  # noqa: F401
    from binance_mcp.service import BinanceService

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-binance", version="0.0.1")
    servicer = BinanceService(base_url=backend_url)
    srv.register(servicer, service_name="binance.v1.BinanceMarketService")
    yield srv
    srv.stop()
