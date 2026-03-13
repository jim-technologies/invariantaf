"""Shared fixtures for DexScreener MCP integration tests."""

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

PAIR = {
    "chainId": "ethereum",
    "dexId": "uniswap",
    "url": "https://dexscreener.com/ethereum/0xabcdef",
    "pairAddress": "0xabcdef1234567890abcdef1234567890abcdef12",
    "labels": ["v3"],
    "baseToken": {
        "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "name": "Wrapped Ether",
        "symbol": "WETH",
    },
    "quoteToken": {
        "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "name": "Tether USD",
        "symbol": "USDT",
    },
    "priceNative": "1.0",
    "priceUsd": "2100.50",
    "txns": {
        "m5": {"buys": 10, "sells": 5},
        "h1": {"buys": 120, "sells": 80},
        "h6": {"buys": 700, "sells": 500},
        "h24": {"buys": 2800, "sells": 2100},
    },
    "volume": {
        "m5": 50000.0,
        "h1": 600000.0,
        "h6": 3500000.0,
        "h24": 14000000.0,
    },
    "priceChange": {
        "m5": 0.05,
        "h1": -0.3,
        "h6": 1.2,
        "h24": 2.5,
    },
    "liquidity": {
        "usd": 5000000.0,
        "base": 1200.5,
        "quote": 2500000.0,
    },
    "fdv": 250000000.0,
    "marketCap": 250000000.0,
    "pairCreatedAt": 1669602341000,
}

TOKEN_PROFILE = {
    "url": "https://dexscreener.com/ethereum/0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "chainId": "ethereum",
    "tokenAddress": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "icon": "https://example.com/icon.png",
    "header": "https://example.com/header.png",
    "openGraph": "https://example.com/og.png",
    "description": "Wrapped Ether token",
    "links": [
        {"label": "Website", "type": "website", "url": "https://weth.io"},
        {"type": "twitter", "url": "https://twitter.com/weth"},
    ],
}

BOOSTED_TOKEN = {
    "url": "https://dexscreener.com/solana/abc123",
    "chainId": "solana",
    "tokenAddress": "abc123def456",
    "description": "A boosted token",
    "icon": "https://example.com/icon.png",
    "header": "https://example.com/header.png",
    "openGraph": "https://example.com/og.png",
    "links": [
        {"type": "twitter", "url": "https://twitter.com/token"},
    ],
    "totalAmount": 500.0,
    "amount": 100.0,
}

TOKEN_ORDER = {
    "chainId": "solana",
    "tokenAddress": "abc123def456",
    "type": "tokenProfile",
    "status": "approved",
    "paymentTimestamp": 1700000000000,
}

TOKEN_BOOST = {
    "chainId": "solana",
    "tokenAddress": "abc123def456",
    "id": "boost-001",
    "amount": 50.0,
    "paymentTimestamp": 1700001000000,
}


class _DexScreenerHandler(BaseHTTPRequestHandler):
    """Mock DexScreener API backend for integration tests."""

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path

        if path == "/latest/dex/search":
            self._write_json(200, {"pairs": [PAIR]})
            return

        if path.startswith("/latest/dex/pairs/"):
            self._write_json(200, {"pairs": [PAIR]})
            return

        if path.startswith("/latest/dex/tokens/"):
            self._write_json(200, {"pairs": [PAIR]})
            return

        if path == "/token-profiles/latest/v1":
            self._write_json(200, [TOKEN_PROFILE])
            return

        if path == "/token-boosts/latest/v1":
            self._write_json(200, [BOOSTED_TOKEN])
            return

        if path == "/token-boosts/top/v1":
            self._write_json(200, [BOOSTED_TOKEN])
            return

        if path.startswith("/orders/v1/"):
            self._write_json(200, [TOKEN_ORDER])
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


@pytest.fixture
def backend_url():
    httpd = ThreadingHTTPServer(("localhost", 0), _DexScreenerHandler)
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
    from dexscreener_mcp.gen.dexscreener.v1 import dexscreener_pb2 as _dexscreener_pb2  # noqa: F401
    from dexscreener_mcp.service import DexScreenerService

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-dexscreener", version="0.0.1")
    servicer = DexScreenerService(base_url=backend_url)
    srv.register(servicer, service_name="dexscreener.v1.DexScreenerService")
    yield srv
    srv.stop()
