"""Shared fixtures for GeckoTerminal MCP integration tests."""

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

# --- Mock data in JSON:API format ---

NETWORK = {
    "id": "eth",
    "type": "network",
    "attributes": {
        "name": "Ethereum",
        "coingecko_asset_platform_id": "ethereum",
    },
}

POOL_ATTRIBUTES = {
    "address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
    "name": "USDC / WETH 0.05%",
    "base_token_price_usd": "3456.78",
    "quote_token_price_usd": "1.0",
    "fdv_usd": "5000000000.0",
    "market_cap_usd": "3000000000.0",
    "reserve_in_usd": "250000000.0",
    "volume_usd": {
        "m5": "50000.0",
        "h1": "1200000.0",
        "h24": "28000000.0",
    },
    "price_change_percentage": {
        "m5": "0.12",
        "h1": "1.5",
        "h24": "-2.3",
    },
    "pool_created_at": "2023-01-15T10:30:00Z",
}

POOL_RESOURCE = {
    "id": "eth_0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
    "type": "pool",
    "attributes": POOL_ATTRIBUTES,
    "relationships": {
        "base_token": {
            "data": {"id": "eth_0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "type": "token"},
        },
        "quote_token": {
            "data": {"id": "eth_0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", "type": "token"},
        },
        "network": {
            "data": {"id": "eth", "type": "network"},
        },
        "dex": {
            "data": {"id": "uniswap_v3", "type": "dex"},
        },
    },
}

OHLCV_DATA = {
    "id": "ohlcv",
    "type": "ohlcv",
    "attributes": {
        "ohlcv_list": [
            [1700000000, "3400.0", "3500.0", "3350.0", "3450.0", "1000000.0"],
            [1700003600, "3450.0", "3480.0", "3420.0", "3460.0", "800000.0"],
            [1700007200, "3460.0", "3520.0", "3440.0", "3510.0", "1200000.0"],
        ],
    },
}


class _GeckoTerminalHandler(BaseHTTPRequestHandler):
    """Mock GeckoTerminal API backend for integration tests."""

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        query = self._parse_query()

        # GET /api/v2/networks
        if path == "/api/v2/networks":
            self._write_jsonapi_list([NETWORK])
            return

        # GET /api/v2/networks/trending_pools
        if path == "/api/v2/networks/trending_pools":
            self._write_jsonapi_list([POOL_RESOURCE])
            return

        # GET /api/v2/networks/{network}/trending_pools
        if path.startswith("/api/v2/networks/") and path.endswith("/trending_pools"):
            self._write_jsonapi_list([POOL_RESOURCE])
            return

        # GET /api/v2/networks/{network}/pools/{address}
        parts = path.split("/")
        if (
            len(parts) == 7
            and parts[1] == "api"
            and parts[2] == "v2"
            and parts[3] == "networks"
            and parts[5] == "pools"
        ):
            self._write_jsonapi_single(POOL_RESOURCE)
            return

        # GET /api/v2/search/pools
        if path == "/api/v2/search/pools":
            self._write_jsonapi_list([POOL_RESOURCE])
            return

        # GET /api/v2/networks/{network}/pools/{address}/ohlcv/{timeframe}
        if "/ohlcv/" in path:
            self._write_jsonapi_single(OHLCV_DATA)
            return

        # GET /api/v2/networks/{network}/new_pools
        if path.startswith("/api/v2/networks/") and path.endswith("/new_pools"):
            self._write_jsonapi_list([POOL_RESOURCE])
            return

        # GET /api/v2/networks/{network}/dexes/{dex}/pools
        if "/dexes/" in path and path.endswith("/pools"):
            self._write_jsonapi_list([POOL_RESOURCE])
            return

        self.send_response(404)
        self.end_headers()

    def _parse_query(self) -> dict[str, str]:
        if "?" not in self.path:
            return {}
        qs = self.path.split("?", 1)[1]
        params = urllib.parse.parse_qs(qs)
        return {k: v[0] for k, v in params.items()}

    def _write_jsonapi_list(self, data: list):
        """Write a JSON:API list response."""
        self._write_json(200, {"data": data})

    def _write_jsonapi_single(self, data: dict):
        """Write a JSON:API single-resource response."""
        self._write_json(200, {"data": data})

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
    httpd = ThreadingHTTPServer(("localhost", 0), _GeckoTerminalHandler)
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
    from geckoterminal_mcp.gen.geckoterminal.v1 import geckoterminal_pb2 as _pb2  # noqa: F401
    from geckoterminal_mcp.service import GeckoTerminalService

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-geckoterminal", version="0.0.1")
    servicer = GeckoTerminalService(base_url=backend_url)
    srv.register(servicer, service_name="geckoterminal.v1.GeckoTerminalService")
    yield srv
    srv.stop()
