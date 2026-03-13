"""Shared fixtures for CryptoCompare MCP integration tests."""

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

PRICE_RESPONSE = {"USD": 64500.0, "EUR": 59000.0, "GBP": 51000.0}

MULTI_PRICE_RESPONSE = {
    "BTC": {"USD": 64500.0, "EUR": 59000.0},
    "ETH": {"USD": 2500.0, "EUR": 2300.0},
}

FULL_PRICE_RESPONSE = {
    "RAW": {
        "BTC": {
            "USD": {
                "PRICE": 64500.0,
                "VOLUME24HOUR": 25000.0,
                "MKTCAP": 1250000000000.0,
                "CHANGEPCT24HOUR": 2.5,
                "HIGH24HOUR": 65000.0,
                "LOW24HOUR": 63000.0,
                "OPEN24HOUR": 63500.0,
                "SUPPLY": 19500000.0,
            }
        },
        "ETH": {
            "USD": {
                "PRICE": 2500.0,
                "VOLUME24HOUR": 150000.0,
                "MKTCAP": 300000000000.0,
                "CHANGEPCT24HOUR": 1.8,
                "HIGH24HOUR": 2550.0,
                "LOW24HOUR": 2450.0,
                "OPEN24HOUR": 2470.0,
                "SUPPLY": 120000000.0,
            }
        },
    }
}

HISTO_CANDLES = [
    {"time": 1700000000, "open": 64000.0, "high": 64600.0, "low": 63900.0, "close": 64500.0, "volumefrom": 100.0, "volumeto": 6450000.0},
    {"time": 1700003600, "open": 64500.0, "high": 64800.0, "low": 64200.0, "close": 64300.0, "volumefrom": 120.0, "volumeto": 7716000.0},
    {"time": 1700007200, "open": 64300.0, "high": 64500.0, "low": 64100.0, "close": 64400.0, "volumefrom": 80.0, "volumeto": 5152000.0},
]

TOP_BY_VOLUME_RESPONSE = {
    "Data": [
        {
            "CoinInfo": {"Name": "BTC", "FullName": "Bitcoin"},
            "RAW": {
                "USD": {
                    "PRICE": 64500.0,
                    "VOLUME24HOUR": 25000.0,
                    "MKTCAP": 1250000000000.0,
                    "CHANGEPCT24HOUR": 2.5,
                }
            },
        },
        {
            "CoinInfo": {"Name": "ETH", "FullName": "Ethereum"},
            "RAW": {
                "USD": {
                    "PRICE": 2500.0,
                    "VOLUME24HOUR": 150000.0,
                    "MKTCAP": 300000000000.0,
                    "CHANGEPCT24HOUR": 1.8,
                }
            },
        },
    ]
}


class _CryptoCompareHandler(BaseHTTPRequestHandler):
    """Mock CryptoCompare API backend for integration tests."""

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path

        if path == "/data/price":
            self._write_json(200, PRICE_RESPONSE)
            return

        if path == "/data/pricemulti":
            self._write_json(200, MULTI_PRICE_RESPONSE)
            return

        if path == "/data/pricemultifull":
            self._write_json(200, FULL_PRICE_RESPONSE)
            return

        if path == "/data/v2/histohour":
            self._write_json(200, {"Data": {"Data": HISTO_CANDLES}})
            return

        if path == "/data/v2/histoday":
            self._write_json(200, {"Data": {"Data": HISTO_CANDLES}})
            return

        if path == "/data/top/totalvolfull":
            self._write_json(200, TOP_BY_VOLUME_RESPONSE)
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
    httpd = ThreadingHTTPServer(("localhost", 0), _CryptoCompareHandler)
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
    from cryptocompare_mcp.gen.cryptocompare.v1 import cryptocompare_pb2 as _cryptocompare_pb2  # noqa: F401
    from cryptocompare_mcp.service import CryptoCompareService

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-cryptocompare", version="0.0.1")
    servicer = CryptoCompareService(base_url=backend_url)
    srv.register(servicer, service_name="cryptocompare.v1.CryptoCompareService")
    yield srv
    srv.stop()
