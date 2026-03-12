"""Live integration tests for Kalshi API -- hits the real API.

Run with:
    KALSHI_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) Kalshi endpoints.
Set KALSHI_BASE_URL to override the default API base URL.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

pytestmark = pytest.mark.skipif(
    os.getenv("KALSHI_RUN_LIVE_TESTS") != "1",
    reason="Set KALSHI_RUN_LIVE_TESTS=1 to run live Kalshi API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from gen.kalshi.v1 import kalshi_pb2 as _kalshi_pb2  # noqa: F401

    base_url = (
        os.getenv("KALSHI_BASE_URL")
        or "https://api.elections.kalshi.com/trade-api/v2"
    ).rstrip("/")
    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-kalshi-live", version="0.0.1"
    )
    srv.connect_http(base_url, service_name="kalshi.v1.KalshiService")
    yield srv
    srv.stop()


# --- Exchange metadata ---


class TestLiveExchange:
    def test_get_exchange_status(self, live_server):
        result = live_server._cli(["KalshiService", "GetExchangeStatus"])
        assert "data" in result
        data = result["data"]
        assert isinstance(data.get("exchange_active"), bool)

    def test_get_exchange_schedule(self, live_server):
        result = live_server._cli(["KalshiService", "GetExchangeSchedule"])
        assert "data" in result
        data = result["data"]
        assert "schedule" in data or isinstance(data, dict)

    def test_get_exchange_announcements(self, live_server):
        result = live_server._cli(["KalshiService", "GetExchangeAnnouncements"])
        assert "data" in result


# --- Shared fixtures for market/event discovery ---


@pytest.fixture(scope="module")
def market_ticker(live_server):
    """Discover a valid market ticker once for all tests that need one."""
    result = live_server._cli(
        ["KalshiService", "GetMarkets", "-r", '{"limit": 1}']
    )
    markets = result["data"]["markets"]
    assert markets, "expected at least one market"
    return markets[0]["ticker"]


@pytest.fixture(scope="module")
def event_info(live_server):
    """Discover event info (event_ticker, series_ticker, market ticker) once."""
    result = live_server._cli(
        ["KalshiService", "GetEvents", "-r", '{"limit": 5}']
    )
    events = result["data"]["events"]
    assert events, "expected at least one event"
    return events


# --- Markets ---


class TestLiveMarkets:
    def test_get_markets(self, live_server):
        result = live_server._cli(
            ["KalshiService", "GetMarkets", "-r", '{"limit": 3}']
        )
        assert "data" in result
        markets = result["data"].get("markets")
        assert isinstance(markets, list)
        assert len(markets) > 0
        m = markets[0]
        assert "ticker" in m
        assert "title" in m or "subtitle" in m
        assert "status" in m

    def test_get_markets_pagination(self, live_server):
        # Fetch page 1
        result1 = live_server._cli(
            ["KalshiService", "GetMarkets", "-r", '{"limit": 2}']
        )
        markets1 = result1["data"]["markets"]
        cursor = result1["data"].get("cursor", "")
        if not cursor:
            pytest.skip("No second page available")

        # Fetch page 2 with cursor
        result2 = live_server._cli(
            [
                "KalshiService",
                "GetMarkets",
                "-r",
                json.dumps({"limit": 2, "cursor": cursor}),
            ]
        )
        markets2 = result2["data"]["markets"]
        assert len(markets2) > 0

    def test_get_market_by_ticker(self, live_server, market_ticker):
        result = live_server._cli(
            ["KalshiService", "GetMarket", "-r", json.dumps({"ticker": market_ticker})]
        )
        assert "data" in result
        assert result["data"]["market"]["ticker"] == market_ticker


# --- Events ---


class TestLiveEvents:
    def test_get_events(self, live_server):
        result = live_server._cli(
            ["KalshiService", "GetEvents", "-r", '{"limit": 3}']
        )
        assert "data" in result
        events = result["data"].get("events")
        assert isinstance(events, list)
        assert len(events) > 0
        e = events[0]
        assert "event_ticker" in e
        assert "title" in e

    def test_get_event(self, live_server, event_info):
        event_ticker = event_info[0]["event_ticker"]
        result = live_server._cli(
            [
                "KalshiService",
                "GetEvent",
                "-r",
                json.dumps({"event_ticker": event_ticker}),
            ]
        )
        assert "data" in result
        assert result["data"]["event"]["event_ticker"] == event_ticker


# --- Series ---


class TestLiveSeries:
    def test_get_series_list(self, live_server):
        result = live_server._cli(["KalshiService", "GetSeriesList"])
        assert "data" in result


# --- Market data ---


class TestLiveMarketData:
    def test_get_market_orderbook(self, live_server, market_ticker):
        result = live_server._cli(
            [
                "KalshiService",
                "GetMarketOrderbook",
                "-r",
                json.dumps({"ticker": market_ticker}),
            ]
        )
        assert "data" in result
        ob = result["data"]
        # Response may contain "orderbook" or "orderbook_fp" depending on the market
        assert "orderbook" in ob or "orderbook_fp" in ob or "yes" in ob or "no" in ob

    def test_get_trades(self, live_server, market_ticker):
        result = live_server._cli(
            [
                "KalshiService",
                "GetTrades",
                "-r",
                json.dumps({"ticker": market_ticker, "limit": 5}),
            ]
        )
        assert "data" in result

    def test_get_market_candlesticks(self, live_server, event_info):
        # Find a series_ticker and a market ticker within that series
        series_ticker = None
        ticker = None
        for event in event_info:
            st = event.get("series_ticker", "")
            mkt = event.get("markets", [])
            if st and mkt:
                series_ticker = st
                ticker = mkt[0].get("ticker", "")
                if ticker:
                    break

        if not series_ticker or not ticker:
            pytest.skip("cannot find series_ticker + market ticker for candlestick test")

        result = live_server._cli(
            [
                "KalshiService",
                "GetMarketCandlesticks",
                "-r",
                json.dumps({
                    "series_ticker": series_ticker,
                    "ticker": ticker,
                    "period_interval": 60,
                }),
            ]
        )
        assert "data" in result
