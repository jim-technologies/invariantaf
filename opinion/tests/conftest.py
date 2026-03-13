"""Shared fixtures for Opinion.trade MCP proxy tests."""

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

MARKET = {
    "marketId": 101,
    "marketTitle": "Will BTC hit $200k by 2027?",
    "status": "activated",
    "statusEnum": 1,
    "marketType": 0,
    "yesLabel": "Yes",
    "noLabel": "No",
    "volume": 500000.0,
    "volume24h": 12000.0,
    "volume7d": 80000.0,
    "createdAt": "2026-01-01T00:00:00Z",
    "cutoffAt": "2027-12-31T23:59:59Z",
    "tokens": [
        {"tokenId": "tok-yes-101", "outcome": "Yes", "price": 0.62},
        {"tokenId": "tok-no-101", "outcome": "No", "price": 0.38},
    ],
    "conditions": [
        {"conditionId": "cond-101", "outcome": "Yes"},
    ],
    "rules": "Resolves Yes if BTC >= $200k on 2027-12-31.",
    "slug": "btc-200k-2027",
    "chainId": "137",
}

MARKET_2 = {
    "marketId": 102,
    "marketTitle": "Will ETH flip BTC?",
    "status": "activated",
    "statusEnum": 1,
    "marketType": 0,
    "yesLabel": "Yes",
    "noLabel": "No",
    "volume": 120000.0,
    "volume24h": 3500.0,
    "volume7d": 25000.0,
    "createdAt": "2026-02-15T00:00:00Z",
    "cutoffAt": "2027-06-30T23:59:59Z",
    "tokens": [],
    "conditions": [],
    "rules": "",
    "slug": "eth-flip-btc",
    "chainId": "137",
}

CATEGORICAL_MARKET = {
    "parent": MARKET,
    "childMarkets": [MARKET, MARKET_2],
}

LATEST_PRICE = {
    "tokenId": "tok-yes-101",
    "price": "0.62",
    "side": "BUY",
    "size": "150",
    "timestamp": "1772720841",
}

ORDERBOOK = {
    "market": "mkt-101",
    "tokenId": "tok-yes-101",
    "timestamp": "1772720841",
    "bids": [
        {"price": "0.61", "size": "200"},
        {"price": "0.60", "size": "350"},
    ],
    "asks": [
        {"price": "0.63", "size": "180"},
        {"price": "0.64", "size": "400"},
    ],
}

PRICE_HISTORY = {
    "history": [
        {"t": 1772720000, "p": "0.60"},
        {"t": 1772723600, "p": "0.61"},
        {"t": 1772727200, "p": "0.62"},
    ],
}

TRADE = {
    "txHash": "0xabc123",
    "marketId": 101,
    "marketTitle": "Will BTC hit $200k by 2027?",
    "side": "BUY",
    "outcome": "Yes",
    "price": "0.60",
    "shares": "100",
    "amount": "60.00",
    "fee": "0.30",
    "profit": "0.00",
    "quoteToken": "USDC",
    "usdAmount": "60.00",
    "statusEnum": 1,
    "chainId": "137",
    "createdAt": "2026-03-01T10:00:00Z",
}

QUOTE_TOKEN = {
    "tokenAddress": "0xUSDC",
    "symbol": "USDC",
    "name": "USD Coin",
    "decimals": 6,
    "chainId": "137",
}


class _OpinionHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # GET /market — list markets
        if path == "/market":
            self._json(200, {"total": 2, "list": [MARKET, MARKET_2]})
            return

        # GET /market/categorical/{marketId}
        if path.startswith("/market/categorical/"):
            self._json(200, CATEGORICAL_MARKET)
            return

        # GET /market/slug/{slug}
        if path.startswith("/market/slug/"):
            slug = path.rsplit("/", 1)[-1]
            if slug == MARKET["slug"]:
                self._json(200, MARKET)
            else:
                self._json(404, {"error": "not found"})
            return

        # GET /market/{marketId}
        if path.startswith("/market/"):
            try:
                market_id = int(path.rsplit("/", 1)[-1])
            except ValueError:
                self._json(400, {"error": "bad market_id"})
                return
            if market_id == MARKET["marketId"]:
                self._json(200, MARKET)
            else:
                self._json(404, {"error": "not found"})
            return

        # GET /token/latest-price
        if path == "/token/latest-price":
            self._json(200, LATEST_PRICE)
            return

        # GET /token/orderbook
        if path == "/token/orderbook":
            self._json(200, ORDERBOOK)
            return

        # GET /token/price-history
        if path == "/token/price-history":
            self._json(200, PRICE_HISTORY)
            return

        # GET /trade/user/{walletAddress}
        if path.startswith("/trade/user/"):
            self._json(200, {"total": 1, "list": [TRADE]})
            return

        # GET /quoteToken
        if path == "/quoteToken":
            self._json(200, [QUOTE_TOKEN])
            return

        self.send_response(404)
        self.end_headers()

    def _json(self, status: int, payload: object):
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
def opinion_url():
    httpd, url = _run_backend(_OpinionHandler)
    try:
        yield url
    finally:
        httpd.shutdown()


@pytest.fixture
def server(opinion_url: str):
    from invariant import Server
    from gen.opinion.v1 import opinion_pb2 as _opinion_pb2  # noqa: F401

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-opinion", version="0.0.1")
    srv.connect_http(opinion_url, service_name="opinion.v1.OpinionService")
    yield srv
    srv.stop()
