"""Shared fixtures for Kraken MCP integration tests."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

SPOT_API_KEY = "spot-key"
SPOT_API_SECRET_RAW = b"spot-secret"
SPOT_API_SECRET = base64.b64encode(SPOT_API_SECRET_RAW).decode()

FUTURES_API_KEY = "futures-key"
FUTURES_API_SECRET_RAW = b"futures-secret"
FUTURES_API_SECRET = base64.b64encode(FUTURES_API_SECRET_RAW).decode()


class _SpotHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path

        if path == "/0/public/Time":
            self._write_json(
                200,
                {
                    "error": [],
                    "result": {
                        "unixtime": 1700000000,
                        "rfc1123": "Wed, 15 Nov 2023 12:26:40 GMT",
                    },
                },
            )
            return

        if path == "/0/public/SystemStatus":
            self._write_json(200, {"error": [], "result": {"status": "online", "timestamp": "2026-03-06T00:00:00Z"}})
            return

        if path == "/0/public/AssetPairs":
            self._write_json(
                200,
                {
                    "error": [],
                    "result": {
                        "XBTUSD": {
                            "altname": "XBTUSD",
                            "wsname": "XBT/USD",
                            "aclass_base": "currency",
                            "base": "XXBT",
                            "aclass_quote": "currency",
                            "quote": "ZUSD",
                            "lot": "unit",
                            "pair_decimals": 1,
                            "cost_decimals": 5,
                            "lot_decimals": 8,
                            "lot_multiplier": 1,
                            "leverage_buy": [2, 3],
                            "leverage_sell": [2, 3],
                            "fees": [[0, 0.26], [50000, 0.24]],
                            "fees_maker": [[0, 0.16], [50000, 0.14]],
                            "fee_volume_currency": "ZUSD",
                            "margin_call": 80,
                            "margin_stop": 40,
                            "ordermin": "0.0002",
                            "costmin": "10",
                            "tick_size": "0.1",
                            "status": "online",
                            "long_position_limit": 100,
                            "short_position_limit": 100,
                        }
                    },
                },
            )
            return

        if path == "/0/public/Ticker":
            self._write_json(
                200,
                {
                    "error": [],
                    "result": {
                        "XBTUSD": {
                            "a": ["30001.0", "1", "1.2"],
                            "b": ["30000.0", "2", "2.4"],
                            "c": ["30000.5", "0.5"],
                            "v": ["100", "200"],
                            "p": ["29900", "29800"],
                            "t": [10, 20],
                            "l": ["29000", "28000"],
                            "h": ["31000", "32000"],
                            "o": "29500",
                        }
                    },
                },
            )
            return

        if path == "/0/public/Depth":
            self._write_json(
                200,
                {
                    "error": [],
                    "result": {
                        "XBTUSD": {
                            "asks": [["30001.0", "1.1", 1700000001]],
                            "bids": [["30000.0", "0.9", 1700000002]],
                        }
                    },
                },
            )
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        body = self._read_body_text()

        if path.startswith("/0/private/"):
            if not self._validate_spot_auth(path, body):
                self._write_json(401, {"error": ["EAPI:Invalid signature"]})
                return

        if path == "/0/private/Balance":
            self._write_json(200, {"error": [], "result": {"ZUSD": "1000.0", "XXBT": "0.42"}})
            return

        if path == "/0/private/OpenOrders":
            self._write_json(
                200,
                {
                    "error": [],
                    "result": {
                        "open": {
                            "OABC": {
                                "refid": None,
                                "userref": 42,
                                "cl_ord_id": "client-1",
                                "status": "open",
                                "opentm": 1700000000,
                                "starttm": 0,
                                "expiretm": 0,
                                "descr": {
                                    "pair": "XBTUSD",
                                    "type": "buy",
                                    "ordertype": "limit",
                                    "price": "30000",
                                    "price2": "0",
                                    "leverage": "none",
                                    "order": "buy 1 XBTUSD @ limit 30000",
                                    "close": "",
                                },
                                "vol": "1.0",
                                "vol_exec": "0.0",
                                "cost": "0.0",
                                "fee": "0.0",
                                "price": "0.0",
                                "stopprice": "0.0",
                                "limitprice": "0.0",
                                "trigger": "last",
                                "margin": False,
                                "misc": "",
                                "sender_sub_id": None,
                                "oflags": "post",
                                "trades": [],
                            }
                        }
                    },
                },
            )
            return

        if path == "/0/private/AddOrder":
            self._write_json(
                200,
                {
                    "error": [],
                    "result": {
                        "descr": {
                            "order": "buy 1.0 XBTUSD @ limit 30000",
                            "close": "",
                        },
                        "txid": ["OABC-123"],
                    },
                },
            )
            return

        if path == "/0/private/CancelOrder":
            self._write_json(200, {"error": [], "result": {"count": 1, "pending": False}})
            return

        if path == "/0/private/CancelAll":
            self._write_json(200, {"error": [], "result": {"count": 2, "pending": False}})
            return

        if path == "/0/private/CancelAllOrdersAfter":
            self._write_json(
                200,
                {
                    "error": [],
                    "result": {
                        "currentTime": "2026-03-06T00:00:00Z",
                        "triggerTime": "2026-03-06T00:01:00Z",
                    },
                },
            )
            return

        self.send_response(404)
        self.end_headers()

    def _validate_spot_auth(self, path: str, body_text: str) -> bool:
        if self.headers.get("API-Key") != SPOT_API_KEY:
            return False
        api_sign = self.headers.get("API-Sign")
        if not api_sign:
            return False

        params = urllib.parse.parse_qs(body_text, keep_blank_values=True)
        nonce = (params.get("nonce") or [""])[0]
        if not nonce:
            return False

        digest = hashlib.sha256((nonce + body_text).encode()).digest()
        message = path.encode() + digest
        expected = base64.b64encode(hmac.new(SPOT_API_SECRET_RAW, message, hashlib.sha512).digest()).decode()
        return hmac.compare_digest(api_sign, expected)

    def _read_body_text(self) -> str:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b""
        return raw.decode()

    def _write_json(self, status: int, payload: dict):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format, *args):
        pass


class _FuturesHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path

        if path.startswith("/derivatives/api/v3/") and path in {
            "/derivatives/api/v3/openorders",
            "/derivatives/api/v3/openpositions",
            "/derivatives/api/v3/fills",
        }:
            if not self._validate_futures_auth(parsed.path, parsed.query, ""):
                self._write_json(401, {"result": "error", "error": "authenticationError", "serverTime": "2026-03-06T00:00:00Z"})
                return

        if path == "/derivatives/api/v3/instruments":
            self._write_json(
                200,
                {
                    "result": "success",
                    "serverTime": "2026-03-06T00:00:00Z",
                    "instruments": [
                        {
                            "symbol": "PF_XBTUSD",
                            "pair": "XBTUSD",
                            "base": "XBT",
                            "quote": "USD",
                            "tickSize": 0.5,
                            "tradeable": True,
                            "tradfi": False,
                            "type": "futures_vanilla",
                        }
                    ],
                },
            )
            return

        if path == "/derivatives/api/v3/tickers":
            self._write_json(
                200,
                {
                    "result": "success",
                    "serverTime": "2026-03-06T00:00:00Z",
                    "tickers": [
                        {
                            "symbol": "PF_XBTUSD",
                            "tag": "perpetual",
                            "pair": "XBTUSD",
                            "last": 30000.1,
                            "markPrice": 30000.0,
                            "vol24h": 1234.5,
                            "volumeQuote": 987654.3,
                            "openInterest": 100.2,
                            "suspended": False,
                            "indexPrice": 29999.9,
                            "postOnly": False,
                            "change24h": 1.2,
                        }
                    ],
                },
            )
            return

        if path == "/derivatives/api/v3/orderbook":
            self._write_json(
                200,
                {
                    "result": "success",
                    "serverTime": "2026-03-06T00:00:00Z",
                    "orderBook": {
                        "asks": [[30001.0, 2.0]],
                        "bids": [[30000.0, 1.5]],
                    },
                },
            )
            return

        if path == "/derivatives/api/v3/openorders":
            self._write_json(
                200,
                {
                    "result": "success",
                    "serverTime": "2026-03-06T00:00:00Z",
                    "openOrders": [
                        {
                            "order_id": "ord-1",
                            "cliOrdId": "client-1",
                            "status": "untouched",
                            "side": "buy",
                            "orderType": "lmt",
                            "symbol": "PF_XBTUSD",
                            "limitPrice": 30000.0,
                            "filledSize": 0.0,
                            "unfilledSize": 1.0,
                            "reduceOnly": False,
                            "lastUpdateTime": "2026-03-06T00:00:00Z",
                            "receivedTime": "2026-03-06T00:00:00Z",
                        }
                    ],
                },
            )
            return

        if path == "/derivatives/api/v3/openpositions":
            self._write_json(
                200,
                {
                    "result": "success",
                    "serverTime": "2026-03-06T00:00:00Z",
                    "openPositions": [
                        {
                            "symbol": "PF_XBTUSD",
                            "side": "long",
                            "size": 1.0,
                            "price": 29900.0,
                            "fillTime": "2026-03-06T00:00:00Z",
                            "unrealizedFunding": 0.1,
                        }
                    ],
                },
            )
            return

        if path == "/derivatives/api/v3/fills":
            self._write_json(
                200,
                {
                    "result": "success",
                    "serverTime": "2026-03-06T00:00:00Z",
                    "fills": [
                        {
                            "fill_id": "fill-1",
                            "symbol": "PF_XBTUSD",
                            "side": "buy",
                            "order_id": "ord-1",
                            "size": 0.1,
                            "price": 30000.0,
                            "fillTime": "2026-03-06T00:00:00Z",
                            "fillType": "maker",
                        }
                    ],
                },
            )
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        body = self._read_body_text()

        if path.startswith("/derivatives/api/v3/"):
            if not self._validate_futures_auth(parsed.path, parsed.query, body):
                self._write_json(401, {"result": "error", "error": "authenticationError", "serverTime": "2026-03-06T00:00:00Z"})
                return

        if path == "/derivatives/api/v3/sendorder":
            self._write_json(
                200,
                {
                    "result": "success",
                    "serverTime": "2026-03-06T00:00:00Z",
                    "sendStatus": {
                        "status": "placed",
                        "order_id": "ord-2",
                        "receivedTime": "2026-03-06T00:00:00Z",
                        "orderEvents": [
                            {
                                "type": "PLACE",
                                "order": {
                                    "orderId": "ord-2",
                                    "cliOrdId": "cli-2",
                                    "type": "lmt",
                                    "symbol": "PF_XBTUSD",
                                    "side": "buy",
                                    "quantity": 1.0,
                                    "filled": 0.0,
                                    "limitPrice": 30000.0,
                                    "reduceOnly": False,
                                    "timestamp": "2026-03-06T00:00:00Z",
                                    "lastUpdateTimestamp": "2026-03-06T00:00:00Z",
                                },
                                "reducedQuantity": None,
                            }
                        ],
                    },
                },
            )
            return

        if path == "/derivatives/api/v3/cancelorder":
            self._write_json(
                200,
                {
                    "result": "success",
                    "serverTime": "2026-03-06T00:00:00Z",
                    "cancelStatus": {
                        "status": "cancelled",
                        "order_id": "ord-2",
                        "receivedTime": "2026-03-06T00:00:00Z",
                    },
                },
            )
            return

        self.send_response(404)
        self.end_headers()

    def _validate_futures_auth(self, path: str, query: str, body_text: str) -> bool:
        if self.headers.get("APIKey") != FUTURES_API_KEY:
            return False

        nonce = self.headers.get("Nonce")
        authent = self.headers.get("Authent")
        if not nonce or not authent:
            return False

        endpoint_component = path
        if query:
            endpoint_component += f"?{query}"

        digest = hashlib.sha256((body_text + nonce + endpoint_component).encode()).digest()
        expected = base64.b64encode(hmac.new(FUTURES_API_SECRET_RAW, digest, hashlib.sha512).digest()).decode()
        return hmac.compare_digest(authent, expected)

    def _read_body_text(self) -> str:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b""
        return raw.decode()

    def _write_json(self, status: int, payload: dict):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format, *args):
        pass


@pytest.fixture
def spot_backend_url():
    httpd = ThreadingHTTPServer(("localhost", 0), _SpotHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://localhost:{port}/0"
    finally:
        httpd.shutdown()


@pytest.fixture
def futures_backend_url():
    httpd = ThreadingHTTPServer(("localhost", 0), _FuturesHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://localhost:{port}/derivatives/api/v3"
    finally:
        httpd.shutdown()


@pytest.fixture
def server(spot_backend_url: str, futures_backend_url: str, monkeypatch: pytest.MonkeyPatch):
    from invariant import Server
    from kraken_mcp.gen.kraken.v1 import kraken_pb2 as _kraken_pb2  # noqa: F401
    from kraken_mcp.service import KrakenService

    monkeypatch.setenv("KRAKEN_SPOT_API_KEY", SPOT_API_KEY)
    monkeypatch.setenv("KRAKEN_SPOT_API_SECRET", SPOT_API_SECRET)
    monkeypatch.setenv("KRAKEN_FUTURES_API_KEY", FUTURES_API_KEY)
    monkeypatch.setenv("KRAKEN_FUTURES_API_SECRET", FUTURES_API_SECRET)

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-kraken", version="0.0.1")
    servicer = KrakenService(spot_base_url=spot_backend_url, futures_base_url=futures_backend_url)
    srv.register(servicer, service_name="kraken.v1.KrakenSpotService")
    srv.register(servicer, service_name="kraken.v1.KrakenFuturesService")
    yield srv
    srv.stop()
