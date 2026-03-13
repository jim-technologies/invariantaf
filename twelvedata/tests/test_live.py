"""Live integration tests for Twelve Data API -- hits the real API.

Run with:
    TWELVEDATA_RUN_LIVE_TESTS=1 TWELVEDATA_API_KEY=your_key uv run python -m pytest tests/test_live.py -v

Requires a valid Twelve Data API key (free tier: 800 calls/day, 8/min).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_BASE_URL = "https://api.twelvedata.com"

pytestmark = pytest.mark.skipif(
    os.getenv("TWELVEDATA_RUN_LIVE_TESTS") != "1"
    or not os.getenv("TWELVEDATA_API_KEY", "").strip(),
    reason="Set TWELVEDATA_RUN_LIVE_TESTS=1 and TWELVEDATA_API_KEY to run live Twelve Data API tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    """Call a CLI method; skip on transient errors or rate limiting."""
    import httpx

    args = [service, method]
    if params:
        args.extend(["-r", json.dumps(params)])
    try:
        return live_server._cli(args)
    except (httpx.ConnectTimeout, httpx.ConnectError, httpx.TimeoutException) as exc:
        pytest.skip(f"{method}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        msg = str(exc)
        if any(code in msg for code in ("401", "403", "429", "500", "502", "503", "Timeout", "timed out")):
            pytest.skip(f"{method}: {msg[:120]}")
        raise


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from twelvedata_mcp.gen.twelvedata.v1 import twelvedata_pb2 as _twelvedata_pb2  # noqa: F401
    from twelvedata_mcp.service import TwelveDataService

    base_url = (os.getenv("TWELVEDATA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    api_key = os.getenv("TWELVEDATA_API_KEY", "").strip()

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-twelvedata-live", version="0.0.1"
    )
    servicer = TwelveDataService(base_url=base_url, api_key=api_key)
    srv.register(servicer, service_name="twelvedata.v1.TwelveDataService")
    yield srv
    srv.stop()


# --- GetQuote ---


class TestLiveGetQuote:
    def test_get_aapl_quote(self, live_server):
        result = _cli_or_skip(
            live_server, "TwelveDataService", "GetQuote",
            {"symbol": "AAPL"},
        )
        assert result["symbol"] == "AAPL"
        assert result["name"] != ""
        assert result["close"] > 0

    def test_get_btc_usd_quote(self, live_server):
        result = _cli_or_skip(
            live_server, "TwelveDataService", "GetQuote",
            {"symbol": "BTC/USD"},
        )
        assert result["symbol"] == "BTC/USD"
        assert result["close"] > 0


# --- GetTimeSeries ---


class TestLiveGetTimeSeries:
    def test_aapl_daily(self, live_server):
        result = _cli_or_skip(
            live_server, "TwelveDataService", "GetTimeSeries",
            {"symbol": "AAPL", "interval": "1day", "outputsize": 5},
        )
        assert result["symbol"] == "AAPL"
        assert "values" in result
        values = result["values"]
        assert isinstance(values, list)
        assert len(values) > 0
        assert values[0]["close"] > 0

    def test_btc_usd_1h(self, live_server):
        result = _cli_or_skip(
            live_server, "TwelveDataService", "GetTimeSeries",
            {"symbol": "BTC/USD", "interval": "1h", "outputsize": 5},
        )
        assert result["symbol"] == "BTC/USD"
        assert len(result["values"]) > 0


# --- GetPrice ---


class TestLiveGetPrice:
    def test_aapl_price(self, live_server):
        result = _cli_or_skip(
            live_server, "TwelveDataService", "GetPrice",
            {"symbol": "AAPL"},
        )
        assert result["price"] > 0

    def test_eur_usd_price(self, live_server):
        result = _cli_or_skip(
            live_server, "TwelveDataService", "GetPrice",
            {"symbol": "EUR/USD"},
        )
        assert result["price"] > 0


# --- ListStocks ---


class TestLiveListStocks:
    def test_list_nasdaq_stocks(self, live_server):
        result = _cli_or_skip(
            live_server, "TwelveDataService", "ListStocks",
            {"exchange": "NASDAQ"},
        )
        assert "stocks" in result
        stocks = result["stocks"]
        assert isinstance(stocks, list)
        assert len(stocks) > 0
        assert "symbol" in stocks[0]
        assert "name" in stocks[0]


# --- ListForexPairs ---


class TestLiveListForexPairs:
    def test_list_forex(self, live_server):
        result = _cli_or_skip(
            live_server, "TwelveDataService", "ListForexPairs",
        )
        assert "pairs" in result
        pairs = result["pairs"]
        assert isinstance(pairs, list)
        assert len(pairs) > 0
        assert "symbol" in pairs[0]


# --- ListCryptoPairs ---


class TestLiveListCryptoPairs:
    def test_list_crypto(self, live_server):
        result = _cli_or_skip(
            live_server, "TwelveDataService", "ListCryptoPairs",
        )
        assert "pairs" in result
        pairs = result["pairs"]
        assert isinstance(pairs, list)
        assert len(pairs) > 0
        assert "symbol" in pairs[0]


# --- GetExchangeRate ---


class TestLiveGetExchangeRate:
    def test_usd_eur(self, live_server):
        result = _cli_or_skip(
            live_server, "TwelveDataService", "GetExchangeRate",
            {"symbol": "USD/EUR"},
        )
        assert result["symbol"] == "USD/EUR"
        assert result["rate"] > 0

    def test_btc_usd(self, live_server):
        result = _cli_or_skip(
            live_server, "TwelveDataService", "GetExchangeRate",
            {"symbol": "BTC/USD"},
        )
        assert result["symbol"] == "BTC/USD"
        assert result["rate"] > 0


# --- GetEarningsCalendar ---


class TestLiveGetEarningsCalendar:
    def test_earnings_upcoming(self, live_server):
        result = _cli_or_skip(
            live_server, "TwelveDataService", "GetEarningsCalendar",
        )
        assert "earnings" in result
        earnings = result["earnings"]
        assert isinstance(earnings, list)
        # Earnings calendar may be empty depending on date range
        if len(earnings) > 0:
            assert "symbol" in earnings[0]
            assert "date" in earnings[0]
