"""Shared fixtures for CoinPaprika MCP integration tests."""

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

GLOBAL_DATA = {
    "market_cap_usd": 2500000000000,
    "volume_24h_usd": 120000000000,
    "bitcoin_dominance_percentage": 52.35,
    "cryptocurrencies_number": 10234,
    "market_cap_ath_value": 3000000000000,
    "market_cap_ath_date": "2021-11-10T00:00:00Z",
    "volume_24h_ath_value": 500000000000,
    "volume_24h_ath_date": "2021-05-19T00:00:00Z",
    "volume_24h_percent_from_ath": -76.0,
    "volume_24h_percent_to_ath": 316.67,
    "market_cap_change_24h": 1.25,
    "volume_24h_change_24h": -3.5,
    "last_updated": 1772720841,
}

COIN_SUMMARY = {
    "id": "btc-bitcoin",
    "name": "Bitcoin",
    "symbol": "BTC",
    "rank": 1,
    "is_new": False,
    "is_active": True,
    "type": "coin",
}

COIN_DETAIL = {
    "id": "btc-bitcoin",
    "name": "Bitcoin",
    "symbol": "BTC",
    "rank": 1,
    "is_new": False,
    "is_active": True,
    "type": "coin",
    "description": "Bitcoin is a cryptocurrency and worldwide payment system.",
    "started_at": "2009-01-03T00:00:00Z",
    "open_source": True,
    "development_status": "Working product",
    "hardware_wallet": True,
    "proof_type": "Proof of Work",
    "org_structure": "Decentralized",
    "hash_algorithm": "SHA-256",
    "first_data_at": "2010-07-17T00:00:00Z",
    "last_data_at": "2024-03-01T00:00:00Z",
    "tags": [
        {"id": "segwit", "name": "Segwit", "coin_counter": 25, "ico_counter": 0},
    ],
    "team": [
        {"id": "satoshi-nakamoto", "name": "Satoshi Nakamoto", "position": "Founder"},
    ],
}

TICKER_DATA = {
    "id": "btc-bitcoin",
    "name": "Bitcoin",
    "symbol": "BTC",
    "rank": 1,
    "total_supply": 19600000,
    "max_supply": 21000000,
    "beta_value": 1.05,
    "first_data_at": "2010-07-17T00:00:00Z",
    "last_updated": "2024-03-01T12:00:00Z",
    "quotes": {
        "USD": {
            "price": 64500.0,
            "volume_24h": 35000000000.0,
            "volume_24h_change_24h": -2.5,
            "market_cap": 1264200000000,
            "market_cap_change_24h": 1.1,
            "percent_change_15m": 0.05,
            "percent_change_30m": 0.1,
            "percent_change_1h": 0.25,
            "percent_change_6h": 1.5,
            "percent_change_12h": 2.0,
            "percent_change_24h": 3.0,
            "percent_change_7d": 5.0,
            "percent_change_30d": 10.0,
            "percent_change_1y": 150.0,
            "ath_price": 69000.0,
            "ath_date": "2021-11-10T14:24:00Z",
            "percent_from_price_ath": -6.52,
        },
    },
}

MARKET_ENTRY = {
    "exchange_id": "binance",
    "exchange_name": "Binance",
    "pair": "BTC/USDT",
    "base_currency_id": "btc-bitcoin",
    "base_currency_name": "Bitcoin",
    "quote_currency_id": "usdt-tether",
    "quote_currency_name": "Tether",
    "market_url": "https://www.binance.com/trade/BTC_USDT",
    "category": "Spot",
    "fee_type": "Percentage",
    "outlier": False,
    "adjusted_volume_24h_share": 15.5,
    "quotes": {
        "USD": {
            "price": 64500.0,
            "volume_24h": 5000000000.0,
        },
    },
    "trust_score": "high",
    "last_updated": "2024-03-01T12:00:00Z",
}

OHLCV_ENTRY = {
    "time_open": "2024-03-01T00:00:00Z",
    "time_close": "2024-03-01T23:59:59Z",
    "open": 62500.0,
    "high": 65000.0,
    "low": 62000.0,
    "close": 64500.0,
    "volume": 35000000000,
    "market_cap": 1264200000000,
}

SEARCH_RESULT = {
    "currencies": [
        {
            "id": "btc-bitcoin",
            "name": "Bitcoin",
            "symbol": "BTC",
            "rank": 1,
            "is_new": False,
            "is_active": True,
            "type": "coin",
        },
    ],
}


class _CoinPaprikaHandler(BaseHTTPRequestHandler):
    """Mock CoinPaprika API backend for integration tests."""

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        query = self._parse_query()

        if path == "/global":
            self._write_json(200, GLOBAL_DATA)
            return

        if path == "/coins" and not self._has_subpath(path, "/coins/"):
            self._write_json(200, [COIN_SUMMARY])
            return

        if path == "/coins/btc-bitcoin/markets":
            self._write_json(200, [MARKET_ENTRY])
            return

        if path == "/coins/btc-bitcoin/ohlcv/latest/":
            self._write_json(200, [OHLCV_ENTRY])
            return

        if path == "/coins/btc-bitcoin":
            self._write_json(200, COIN_DETAIL)
            return

        if path == "/tickers/btc-bitcoin":
            self._write_json(200, TICKER_DATA)
            return

        if path == "/tickers" and not self._has_subpath(path, "/tickers/"):
            self._write_json(200, [TICKER_DATA])
            return

        if path == "/search" or path == "/search/":
            self._write_json(200, SEARCH_RESULT)
            return

        self.send_response(404)
        self.end_headers()

    def _has_subpath(self, path: str, prefix: str) -> bool:
        return path.startswith(prefix)

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
    httpd = ThreadingHTTPServer(("localhost", 0), _CoinPaprikaHandler)
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
    from coinpaprika_mcp.gen.coinpaprika.v1 import coinpaprika_pb2 as _coinpaprika_pb2  # noqa: F401
    from coinpaprika_mcp.service import CoinPaprikaService

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-coinpaprika", version="0.0.1")
    servicer = CoinPaprikaService(base_url=backend_url)
    srv.register(servicer, service_name="coinpaprika.v1.CoinPaprikaService")
    yield srv
    srv.stop()
