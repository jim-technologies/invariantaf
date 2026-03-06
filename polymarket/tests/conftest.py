"""Shared fixtures for Polymarket MCP proxy tests."""

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
TEST_PRIVATE_KEY = "0x59c6995e998f97a5a0044966f09453883b7e5a5f20f2f7e7f5f4ed245032e0d2"

MARKET = {
    "id": "456",
    "question": "BTC above $150k?",
    "condition_id": "0xmarket",
    "slug": "test-market",
    "active": True,
    "closed": False,
    "archived": False,
    "accepting_orders": True,
    "accepting_order_timestamp": "1772720000",
    "minimum_order_size": "1",
    "minimum_tick_size": "0.01",
    "liquidity": 250000.0,
    "volume": 190000.0,
    "clobTokenIds": '["tok-yes","tok-no"]',
    "tokens": [
        {"token_id": "tok-yes", "outcome": "Yes", "price": "0.42", "winner": False},
        {"token_id": "tok-no", "outcome": "No", "price": "0.58", "winner": False},
    ],
}

EVENT = {
    "id": "123",
    "slug": "test-event",
    "ticker": "BTC-150K-2026",
    "title": "Will BTC be above $150k?",
    "description": "Synthetic fixture event",
    "startDate": "2026-01-01T00:00:00Z",
    "creationDate": "2025-12-01T00:00:00Z",
    "endDate": "2026-12-31T23:59:59Z",
    "image": "https://example.com/event.png",
    "icon": "https://example.com/icon.png",
    "active": True,
    "closed": False,
    "archived": False,
    "featured": True,
    "restricted": False,
    "new": True,
    "volume": 12345.67,
    "liquidity": 54321.0,
    "openInterest": 2222.2,
    "volume24hr": 120.5,
    "tags": [
        {
            "id": "1",
            "label": "Crypto",
            "slug": "crypto",
            "forceShow": True,
            "createdAt": "2025-12-01T00:00:00Z",
            "updatedAt": "2025-12-01T00:00:00Z",
        }
    ],
    "markets": [MARKET],
}


class _GammaHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/public-search":
            self._write_data(
                {
                    "events": [EVENT],
                    "markets": [MARKET],
                    "profiles": [
                        {
                            "pseudonym": "alpha",
                            "name": "Alpha Trader",
                            "profile_image": "https://example.com/profile.png",
                            "profile_image_thumbnail": "https://example.com/profile-thumb.png",
                            "bio": "maker",
                            "reward_rate": "1.2",
                        }
                    ],
                }
            )
            return
        if path == "/events":
            if query.get("slug") == ["test-event"]:
                self._write_data([EVENT])
            else:
                self._write_data([EVENT, {**EVENT, "id": "124", "slug": "test-event-2"}])
            return
        if path == "/events/slug/test-event":
            self._write_data(EVENT)
            return
        if path == "/events/123":
            self._write_data(EVENT)
            return
        if path == "/markets":
            self._write_data([MARKET])
            return
        if path == "/markets/456":
            self._write_data(MARKET)
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

    def log_message(self, format, *args):  # noqa: A003
        pass


class _ClobHandler(BaseHTTPRequestHandler):
    _AUTH_HEADERS = (
        "POLY_ADDRESS",
        "POLY_SIGNATURE",
        "POLY_TIMESTAMP",
        "POLY_API_KEY",
        "POLY_PASSPHRASE",
    )

    def _assert_auth(self) -> bool:
        for key in self._AUTH_HEADERS:
            if not self.headers.get(key):
                return False
        return self.headers.get("POLY_API_KEY") == "test-api-key"

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        parsed_qs = urllib.parse.parse_qs(parsed.query)

        if path == "/book":
            self._write_data(
                {
                    "market": "0xmarket",
                    "asset_id": "tok-yes",
                    "timestamp": "1772720841",
                    "hash": "0xbookhash",
                    "bids": [{"price": "0.41", "size": "120"}],
                    "asks": [{"price": "0.43", "size": "90"}],
                    "min_order_size": "1",
                    "tick_size": "0.01",
                    "neg_risk": False,
                    "last_trade_price": "0.42",
                }
            )
            return
        if path == "/price":
            self._write_data({"price": "0.42"})
            return
        if path == "/midpoint":
            self._write_data({"mid": "0.42"})
            return
        if path == "/spread":
            self._write_data({"spread": "0.02"})
            return
        if path == "/tick-size":
            self._write_data({"minimum_tick_size": "0.01"})
            return
        if path == "/neg-risk":
            self._write_data({"neg_risk": False})
            return
        if path == "/fee-rate":
            self._write_data({"base_fee": 0})
            return
        if path == "/prices-history":
            self._write_data(
                {
                    "history": [
                        {"t": 1772720841, "p": "0.41"},
                        {"t": 1772720901, "p": "0.42"},
                    ]
                }
            )
            return
        if path == "/data/orders":
            if not self._assert_auth():
                self._write_json(401, {"error": "Unauthorized/Invalid api key"})
                return
            if "next_cursor" not in parsed_qs:
                self._write_json(400, {"error": "missing next_cursor"})
                return
            self._write_data(
                {
                    "limit": 500,
                    "count": 1,
                    "next_cursor": "LTE=",
                    "data": [
                        {
                            "id": "ord-1",
                            "status": "LIVE",
                            "market": "0xmarket",
                            "asset_id": "tok-yes",
                            "price": "0.42",
                            "size": "10",
                            "original_size": "10",
                            "outcome": "Yes",
                            "side": "BUY",
                            "owner": "0xabc",
                            "maker_address": "0xmaker",
                            "expiration": "1772729999",
                            "order_type": "GTC",
                            "created_at": "1772720000",
                        }
                    ],
                }
            )
            return
        if path == "/data/trades":
            if not self._assert_auth():
                self._write_json(401, {"error": "Unauthorized/Invalid api key"})
                return
            if "next_cursor" not in parsed_qs:
                self._write_json(400, {"error": "missing next_cursor"})
                return
            self._write_data(
                {
                    "limit": 500,
                    "count": 1,
                    "next_cursor": "LTE=",
                    "data": [
                        {
                            "id": "trd-1",
                            "status": "MATCHED",
                            "market": "0xmarket",
                            "asset_id": "tok-yes",
                            "price": "0.41",
                            "size": "5",
                            "side": "BUY",
                            "outcome": "Yes",
                            "owner": "0xabc",
                            "maker_address": "0xmaker",
                            "matched_at": "1772721111",
                        }
                    ],
                }
            )
            return
        if path == "/balance-allowance":
            if not self._assert_auth():
                self._write_json(401, {"error": "Unauthorized/Invalid api key"})
                return
            if "signature_type" not in parsed_qs:
                self._write_json(400, {"error": "missing signature_type"})
                return
            self._write_data(
                {
                    "balance": "1000.5",
                    "allowance": "2500.25",
                    "allowances": {
                        "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E": "2500.25",
                        "0xC5d563A36AE78145C45a50134d48A1215220f80a": "0",
                    },
                }
            )
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path != "/order":
            self.send_response(404)
            self.end_headers()
            return
        if not self._assert_auth():
            self._write_json(401, {"error": "Unauthorized/Invalid api key"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode() or "{}")
        order_payload = payload.get("order") if isinstance(payload, dict) else {}
        if not isinstance(order_payload, dict):
            order_payload = {}
        if isinstance(payload, dict) and "order" in payload:
            order_type = str(payload.get("orderType") or "").upper()
            expiration = str(order_payload.get("expiration") or "")
            if order_type != "GTD" and expiration not in {"", "0"}:
                self._write_json(
                    400,
                    {
                        "error": (
                            f"invalid expiration value ({expiration}), "
                            "it should be equal to '0' as the order is not a GTD order"
                        )
                    },
                )
                return

        making_amount = payload.get("makerAmount") or order_payload.get("makerAmount") or "10"
        taking_amount = payload.get("takerAmount") or order_payload.get("takerAmount") or "4.2"
        self._write_data(
            {
                "success": True,
                "errorMsg": "",
                "status": "live",
                "orderID": "ord-1",
                "transactionsHashes": ["0xtx1"],
                "makingAmount": making_amount,
                "takingAmount": taking_amount,
                "echo": payload,
            }
        )

    def do_DELETE(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path

        if not self._assert_auth():
            self._write_json(401, {"error": "Unauthorized/Invalid api key"})
            return

        if path == "/order":
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode() or "{}")
            order_id = payload.get("orderID") or payload.get("order_id") or ""
            self._write_data({"canceled": [order_id], "not_canceled": {}})
            return
        if path == "/cancel-all":
            self._write_data({"canceled": ["ord-1"], "not_canceled": {}})
            return

        self.send_response(404)
        self.end_headers()

    def _write_data(self, payload: object):
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


class _DataHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path

        if path == "/positions":
            self._write_data(
                [
                    {
                        "proxyWallet": "0xabc",
                        "asset": "tok-yes",
                        "conditionId": "0xmarket",
                        "size": "120",
                        "avgPrice": "0.41",
                        "initialValue": "49.2",
                        "currentValue": "50.4",
                        "cashPnl": "1.2",
                        "percentPnl": "2.4",
                        "totalBought": "150",
                        "avgBuyPrice": "0.40",
                        "totalSold": "30",
                        "avgSellPrice": "0.45",
                        "negativeRisk": False,
                        "endDateIso": "2026-12-31T23:59:59Z",
                        "eventSlug": "test-event",
                        "icon": "https://example.com/icon.png",
                        "outcome": "Yes",
                        "title": "Will BTC be above $150k?",
                    }
                ]
            )
            return
        if path in ("/leaderboard", "/v1/leaderboard"):
            self._write_data(
                [
                    {
                        "proxyWallet": "0xabc",
                        "pseudonym": "alpha",
                        "name": "Alpha Trader",
                        "bio": "maker",
                        "profileImage": "https://example.com/profile.png",
                        "profileImageOptimized": {
                            "image_30px": "https://example.com/p-30.png",
                            "image_50px": "https://example.com/p-50.png",
                            "image_120px": "https://example.com/p-120.png",
                            "image_200px": "https://example.com/p-200.png",
                            "image_300px": "https://example.com/p-300.png",
                            "image_400px": "https://example.com/p-400.png",
                        },
                        "volume": 1000.0,
                        "profits": 250.5,
                        "pnl": 230.5,
                        "percentPnl": 23.05,
                        "marketsTraded": 12,
                    }
                ]
            )
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

    def log_message(self, format, *args):  # noqa: A003
        pass


def _run_backend(handler_cls):
    httpd = ThreadingHTTPServer(("localhost", 0), handler_cls)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, f"http://localhost:{port}"


@pytest.fixture
def gamma_url():
    httpd, url = _run_backend(_GammaHandler)
    try:
        yield url
    finally:
        httpd.shutdown()


@pytest.fixture
def clob_url():
    httpd, url = _run_backend(_ClobHandler)
    try:
        yield url
    finally:
        httpd.shutdown()


@pytest.fixture
def data_url():
    httpd, url = _run_backend(_DataHandler)
    try:
        yield url
    finally:
        httpd.shutdown()


@pytest.fixture
def server(gamma_url: str, clob_url: str, data_url: str, monkeypatch: pytest.MonkeyPatch):
    from invariant import Server
    from main import (
        _PolymarketClobCompositeService,
        _build_clob_client,
        _build_clob_defaults_interceptor,
        _build_clob_header_provider,
        _read_signature_type,
    )
    from gen.polymarket.v1 import polymarket_pb2 as _polymarket_pb2  # noqa: F401

    monkeypatch.setenv("POLYMARKET_PRIVATE_KEY", TEST_PRIVATE_KEY)
    monkeypatch.setenv("POLYMARKET_API_KEY", "test-api-key")
    monkeypatch.setenv("POLYMARKET_API_SECRET", "dGVzdA==")
    monkeypatch.setenv("POLYMARKET_API_PASSPHRASE", "test-api-passphrase")

    signature_type_default = _read_signature_type()
    clob_client = _build_clob_client(clob_url, signature_type_default)
    provider = _build_clob_header_provider(clob_client)

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-polymarket", version="0.0.1")
    srv.use(_build_clob_defaults_interceptor(signature_type_default))
    if provider is not None:
        srv.use_http_header_provider(provider)
    srv.connect_http(gamma_url, service_name="polymarket.v1.PolymarketGammaService")
    srv.connect_http(clob_url, service_name="polymarket.v1.PolymarketClobService")
    srv.connect_http(data_url, service_name="polymarket.v1.PolymarketDataService")
    srv.register(
        _PolymarketClobCompositeService(clob_client, signature_type_default),
        service_name="polymarket.v1.PolymarketClobService",
    )
    yield srv
    srv.stop()
