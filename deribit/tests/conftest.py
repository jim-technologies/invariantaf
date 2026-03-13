"""Shared fixtures for Deribit MCP integration tests."""

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

INSTRUMENT = {
    "instrument_name": "BTC-28MAR26-100000-C",
    "kind": "option",
    "base_currency": "BTC",
    "quote_currency": "BTC",
    "settlement_period": "month",
    "min_trade_amount": 0.1,
    "tick_size": 0.0005,
    "strike": 100000.0,
    "option_type": "call",
    "expiration_timestamp": 1774972800000,
    "creation_timestamp": 1772380800000,
    "is_active": True,
}

ORDERBOOK = {
    "instrument_name": "BTC-PERPETUAL",
    "best_bid_price": 64500.0,
    "best_bid_amount": 5.0,
    "best_ask_price": 64510.0,
    "best_ask_amount": 3.0,
    "bids": [[64500.0, 5.0], [64490.0, 10.0]],
    "asks": [[64510.0, 3.0], [64520.0, 7.0]],
    "last_price": 64505.0,
    "mark_price": 64502.5,
    "index_price": 64500.0,
    "open_interest": 250000000.0,
    "funding_8h": 0.00015,
    "current_funding": 0.0001,
    "timestamp": 1772720841000,
    "state": "open",
}

TICKER = {
    "instrument_name": "BTC-PERPETUAL",
    "best_bid_price": 64500.0,
    "best_ask_price": 64510.0,
    "last_price": 64505.0,
    "mark_price": 64502.5,
    "index_price": 64500.0,
    "open_interest": 250000000.0,
    "volume_usd": 500000000.0,
    "high": 65000.0,
    "low": 63500.0,
    "estimated_delivery_price": 64500.0,
    "mark_iv": 55.0,
    "bid_iv": 54.5,
    "ask_iv": 55.5,
    "underlying_price": 64500.0,
    "underlying_index": "BTC-28MAR26",
    "greeks": {
        "delta": 0.65,
        "gamma": 0.0001,
        "vega": 120.5,
        "theta": -35.2,
        "rho": 0.05,
    },
    "funding_8h": 0.00015,
    "interest_rate": 0.0,
    "timestamp": 1772720841000,
}

BOOK_SUMMARY = {
    "instrument_name": "BTC-PERPETUAL",
    "volume_usd": 500000000.0,
    "open_interest": 250000000.0,
    "bid_price": 64500.0,
    "ask_price": 64510.0,
    "last": 64505.0,
    "mark_price": 64502.5,
    "mark_iv": 55.0,
    "underlying_price": 64500.0,
    "underlying_index": "SYN.BTC-28MAR26",
    "interest_rate": 0.0,
    "funding_8h": 0.00015,
}

HISTORICAL_VOLATILITY = [[1772720000000, 55.5], [1772806400000, 56.2], [1772892800000, 54.8]]

TRADINGVIEW_DATA = {
    "ticks": [1772720000000, 1772723600000, 1772727200000],
    "open": [64000.0, 64500.0, 64300.0],
    "high": [64600.0, 64800.0, 64500.0],
    "low": [63900.0, 64200.0, 64100.0],
    "close": [64500.0, 64300.0, 64400.0],
    "volume": [1000.0, 1200.0, 800.0],
    "status": "ok",
}


class _DeribitHandler(BaseHTTPRequestHandler):
    """Mock Deribit API backend for integration tests."""

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        query = self._parse_query()

        if path == "/api/v2/public/get_instruments":
            self._write_result([INSTRUMENT])
            return

        if path == "/api/v2/public/get_order_book":
            self._write_result(ORDERBOOK)
            return

        if path == "/api/v2/public/ticker":
            self._write_result(TICKER)
            return

        if path == "/api/v2/public/get_book_summary_by_currency":
            self._write_result([BOOK_SUMMARY])
            return

        if path == "/api/v2/public/get_historical_volatility":
            self._write_result(HISTORICAL_VOLATILITY)
            return

        if path == "/api/v2/public/get_funding_rate_value":
            self._write_result(0.00025)
            return

        if path == "/api/v2/public/get_index_price":
            self._write_result({
                "index_price": 64500.0,
                "estimated_delivery_price": 64500.0,
            })
            return

        if path == "/api/v2/public/get_tradingview_chart_data":
            self._write_result(TRADINGVIEW_DATA)
            return

        self.send_response(404)
        self.end_headers()

    def _parse_query(self) -> dict[str, str]:
        if "?" not in self.path:
            return {}
        qs = self.path.split("?", 1)[1]
        params = urllib.parse.parse_qs(qs)
        return {k: v[0] for k, v in params.items()}

    def _write_result(self, result: object):
        """Write a Deribit JSON-RPC style response."""
        payload = {"jsonrpc": "2.0", "result": result, "id": 1}
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
    httpd = ThreadingHTTPServer(("localhost", 0), _DeribitHandler)
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
    from deribit_mcp.gen.deribit.v1 import deribit_pb2 as _deribit_pb2  # noqa: F401
    from deribit_mcp.service import DeribitService

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-deribit", version="0.0.1")
    servicer = DeribitService(base_url=backend_url)
    srv.register(servicer, service_name="deribit.v1.DeribitService")
    yield srv
    srv.stop()
