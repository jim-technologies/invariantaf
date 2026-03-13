"""Live integration tests for Deribit API -- hits the real API.

Run with:
    DERIBIT_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) endpoints.
No API keys or credentials needed.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_BASE_URL = "https://www.deribit.com"

pytestmark = pytest.mark.skipif(
    os.getenv("DERIBIT_RUN_LIVE_TESTS") != "1",
    reason="Set DERIBIT_RUN_LIVE_TESTS=1 to run live Deribit API tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    """Call a CLI method; skip on 429/500/502/503 (rate limiting or transient errors)."""
    args = [service, method]
    if params:
        args.extend(["-r", json.dumps(params)])
    try:
        return live_server._cli(args)
    except Exception as exc:
        msg = str(exc)
        for code in ("429", "500", "502", "503"):
            if code in msg:
                pytest.skip(f"{method} returned HTTP {code}")
        raise


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from deribit_mcp.gen.deribit.v1 import deribit_pb2 as _deribit_pb2  # noqa: F401
    from deribit_mcp.service import DeribitService

    base_url = (os.getenv("DERIBIT_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-deribit-live", version="0.0.1"
    )
    servicer = DeribitService(base_url=base_url)
    srv.register(servicer, service_name="deribit.v1.DeribitService")
    yield srv
    srv.stop()


# --- GetInstruments ---


class TestLiveGetInstruments:
    def test_get_btc_options(self, live_server):
        result = _cli_or_skip(
            live_server, "DeribitService", "GetInstruments",
            {"currency": "BTC", "kind": "option"},
        )
        assert "instruments" in result
        instruments = result["instruments"]
        assert isinstance(instruments, list)
        assert len(instruments) > 0
        inst = instruments[0]
        assert "instrument_name" in inst
        assert inst["kind"] == "option"
        assert inst["base_currency"] == "BTC"

    def test_get_btc_futures(self, live_server):
        result = _cli_or_skip(
            live_server, "DeribitService", "GetInstruments",
            {"currency": "BTC", "kind": "future"},
        )
        assert "instruments" in result
        instruments = result["instruments"]
        assert isinstance(instruments, list)
        assert len(instruments) > 0
        assert instruments[0]["kind"] == "future"

    def test_get_eth_instruments(self, live_server):
        result = _cli_or_skip(
            live_server, "DeribitService", "GetInstruments",
            {"currency": "ETH"},
        )
        assert "instruments" in result
        assert len(result["instruments"]) > 0


# --- GetOrderbook ---


class TestLiveGetOrderbook:
    def test_get_orderbook_perpetual(self, live_server):
        result = _cli_or_skip(
            live_server, "DeribitService", "GetOrderbook",
            {"instrument_name": "BTC-PERPETUAL"},
        )
        assert result["instrument_name"] == "BTC-PERPETUAL"
        assert "bids" in result
        assert "asks" in result
        assert len(result["bids"]) > 0
        assert len(result["asks"]) > 0
        assert result["bids"][0]["price"] > 0
        assert result["bids"][0]["amount"] > 0

    def test_get_orderbook_with_depth(self, live_server):
        result = _cli_or_skip(
            live_server, "DeribitService", "GetOrderbook",
            {"instrument_name": "BTC-PERPETUAL", "depth": 5},
        )
        assert len(result["bids"]) <= 5
        assert len(result["asks"]) <= 5


# --- GetTicker ---


class TestLiveGetTicker:
    def test_get_ticker_perpetual(self, live_server):
        result = _cli_or_skip(
            live_server, "DeribitService", "GetTicker",
            {"instrument_name": "BTC-PERPETUAL"},
        )
        assert result["instrument_name"] == "BTC-PERPETUAL"
        assert result["last_price"] > 0
        assert result["mark_price"] > 0
        assert result["index_price"] > 0
        assert result["open_interest"] > 0

    def test_get_ticker_eth(self, live_server):
        result = _cli_or_skip(
            live_server, "DeribitService", "GetTicker",
            {"instrument_name": "ETH-PERPETUAL"},
        )
        assert result["instrument_name"] == "ETH-PERPETUAL"
        assert result["last_price"] > 0


# --- GetBookSummaryByCurrency ---


class TestLiveGetBookSummaryByCurrency:
    def test_btc_futures(self, live_server):
        result = _cli_or_skip(
            live_server, "DeribitService", "GetBookSummaryByCurrency",
            {"currency": "BTC", "kind": "future"},
        )
        assert "summaries" in result
        summaries = result["summaries"]
        assert isinstance(summaries, list)
        assert len(summaries) > 0
        s = summaries[0]
        assert "instrument_name" in s
        assert s["mark_price"] > 0


# --- GetHistoricalVolatility ---


class TestLiveGetHistoricalVolatility:
    def test_btc_volatility(self, live_server):
        result = _cli_or_skip(
            live_server, "DeribitService", "GetHistoricalVolatility",
            {"currency": "BTC"},
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        assert "timestamp" in data[0]
        assert "volatility" in data[0]
        assert data[0]["volatility"] > 0


# --- GetFundingRateValue ---


class TestLiveGetFundingRateValue:
    def test_btc_perpetual_funding(self, live_server):
        now_ms = int(time.time() * 1000)
        eight_hours_ago = now_ms - (8 * 60 * 60 * 1000)
        result = _cli_or_skip(
            live_server, "DeribitService", "GetFundingRateValue",
            {
                "instrument_name": "BTC-PERPETUAL",
                "start_timestamp": eight_hours_ago,
                "end_timestamp": now_ms,
            },
        )
        assert "funding_rate" in result


# --- GetIndexPrice ---


class TestLiveGetIndexPrice:
    def test_btc_usd(self, live_server):
        result = _cli_or_skip(
            live_server, "DeribitService", "GetIndexPrice",
            {"index_name": "btc_usd"},
        )
        assert result["index_price"] > 0

    def test_eth_usd(self, live_server):
        result = _cli_or_skip(
            live_server, "DeribitService", "GetIndexPrice",
            {"index_name": "eth_usd"},
        )
        assert result["index_price"] > 0


# --- GetTradingviewChartData ---


class TestLiveGetTradingviewChartData:
    def test_btc_perpetual_1h(self, live_server):
        now_ms = int(time.time() * 1000)
        one_day_ago = now_ms - (24 * 60 * 60 * 1000)
        result = _cli_or_skip(
            live_server, "DeribitService", "GetTradingviewChartData",
            {
                "instrument_name": "BTC-PERPETUAL",
                "start_timestamp": one_day_ago,
                "end_timestamp": now_ms,
                "resolution": "60",
            },
        )
        assert result["status"] == "ok"
        assert "ticks" in result
        assert len(result["ticks"]) > 0
        assert len(result["open"]) > 0
        assert len(result["close"]) > 0
