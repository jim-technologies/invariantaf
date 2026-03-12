"""Live integration tests for Polymarket API -- hits the real API.

Run with:
    POLYMARKET_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) endpoints:
  - Gamma API: event/market discovery
  - CLOB API: orderbook/pricing data
  - Data API: leaderboard

No CLOB L2 credentials or private key needed.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_GAMMA_BASE_URL = "https://gamma-api.polymarket.com"
DEFAULT_CLOB_BASE_URL = "https://clob.polymarket.com"
DEFAULT_DATA_BASE_URL = "https://data-api.polymarket.com"

pytestmark = pytest.mark.skipif(
    os.getenv("POLYMARKET_RUN_LIVE_TESTS") != "1",
    reason="Set POLYMARKET_RUN_LIVE_TESTS=1 to run live Polymarket API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from gen.polymarket.v1 import polymarket_pb2 as _polymarket_pb2  # noqa: F401

    gamma_base = (
        os.getenv("POLYMARKET_GAMMA_BASE_URL") or DEFAULT_GAMMA_BASE_URL
    ).rstrip("/")
    clob_base = (
        os.getenv("POLYMARKET_CLOB_BASE_URL") or DEFAULT_CLOB_BASE_URL
    ).rstrip("/")
    data_base = (
        os.getenv("POLYMARKET_DATA_BASE_URL") or DEFAULT_DATA_BASE_URL
    ).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-polymarket-live", version="0.0.1"
    )
    srv.connect_http(gamma_base, service_name="polymarket.v1.PolymarketGammaService")
    srv.connect_http(clob_base, service_name="polymarket.v1.PolymarketClobService")
    srv.connect_http(data_base, service_name="polymarket.v1.PolymarketDataService")
    yield srv
    srv.stop()


# --- Gamma API: market discovery ---


class TestLiveGamma:
    @pytest.fixture(scope="class")
    def first_event(self, live_server):
        """Fetch a single event once for all Gamma detail tests."""
        result = live_server._cli(
            [
                "PolymarketGammaService",
                "ListEvents",
                "-r",
                json.dumps({"limit": 1}),
            ]
        )
        events = result["data"]
        assert events, "expected at least one event"
        return events[0]

    def test_search(self, live_server):
        result = live_server._cli(
            [
                "PolymarketGammaService",
                "Search",
                "-r",
                json.dumps({"q": "bitcoin", "limit": 3}),
            ]
        )
        assert "data" in result
        data = result["data"]
        # Search returns events, markets, and profiles
        assert "events" in data or "markets" in data

    def test_list_events(self, live_server):
        result = live_server._cli(
            [
                "PolymarketGammaService",
                "ListEvents",
                "-r",
                json.dumps({"limit": 3}),
            ]
        )
        assert "data" in result
        events = result["data"]
        assert isinstance(events, list)
        assert len(events) > 0
        e = events[0]
        assert "id" in e
        assert "slug" in e or "title" in e

    def test_list_events_with_filter(self, live_server):
        result = live_server._cli(
            [
                "PolymarketGammaService",
                "ListEvents",
                "-r",
                json.dumps({"limit": 2, "active": True}),
            ]
        )
        events = result["data"]
        assert isinstance(events, list)
        for e in events:
            assert e.get("active") is True or e.get("closed") is not True

    def test_get_event_by_slug(self, live_server, first_event):
        slug = first_event["slug"]
        result = live_server._cli(
            [
                "PolymarketGammaService",
                "GetEvent",
                "-r",
                json.dumps({"slug": slug}),
            ]
        )
        assert "data" in result
        assert result["data"]["slug"] == slug

    def test_get_event_by_id(self, live_server, first_event):
        event_id = first_event["id"]
        result = live_server._cli(
            [
                "PolymarketGammaService",
                "GetEventById",
                "-r",
                json.dumps({"id": event_id}),
            ]
        )
        assert "data" in result
        assert result["data"]["id"] == event_id

    def test_get_market_by_slug(self, live_server, first_event):
        markets = first_event.get("markets", [])
        if not markets:
            pytest.skip("no markets in first event")
        slug = markets[0].get("slug") or markets[0].get("condition_id", "")

        result = live_server._cli(
            [
                "PolymarketGammaService",
                "GetMarket",
                "-r",
                json.dumps({"slug": slug}),
            ]
        )
        assert "data" in result

    def test_get_market_by_id(self, live_server, first_event):
        markets = first_event.get("markets", [])
        if not markets:
            pytest.skip("no markets in first event")
        market_id = markets[0]["id"]

        result = live_server._cli(
            [
                "PolymarketGammaService",
                "GetMarketById",
                "-r",
                json.dumps({"id": market_id}),
            ]
        )
        assert "data" in result
        assert result["data"]["id"] == market_id


# --- CLOB API: orderbook / pricing ---


def _extract_token_id(market):
    """Extract the first token_id from a market dict, or None."""
    tokens = market.get("tokens", [])
    if tokens:
        return tokens[0].get("token_id") if isinstance(tokens[0], dict) else tokens[0]
    clob_ids_raw = market.get("clob_token_ids") or market.get("clobTokenIds") or ""
    if clob_ids_raw and clob_ids_raw != "[]":
        try:
            ids = json.loads(clob_ids_raw)
            if ids:
                return ids[0]
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def _market_has_token(market, token_id):
    """Check whether a market contains a given token_id."""
    clob_ids_raw = market.get("clob_token_ids") or market.get("clobTokenIds") or "[]"
    try:
        clob_ids = json.loads(clob_ids_raw) if isinstance(clob_ids_raw, str) else clob_ids_raw
    except (json.JSONDecodeError, TypeError):
        clob_ids = []
    if token_id in clob_ids:
        return True
    for tok in market.get("tokens", []):
        tid = tok.get("token_id") if isinstance(tok, dict) else tok
        if tid == token_id:
            return True
    return False


class TestLiveClob:
    @pytest.fixture(scope="class")
    def active_market_info(self, live_server):
        """Find an active token_id and its condition_id for CLOB tests."""
        result = live_server._cli(
            [
                "PolymarketGammaService",
                "ListEvents",
                "-r",
                json.dumps({"limit": 10, "active": True}),
            ]
        )
        events = result["data"]
        fallback = None
        for event in events:
            for market in event.get("markets", []):
                token_id = _extract_token_id(market)
                if token_id:
                    info = {"token_id": token_id, "condition_id": market.get("condition_id")}
                    if not market.get("closed"):
                        return info
                    if fallback is None:
                        fallback = info

        if fallback:
            return fallback

        pytest.skip("no active market with tokens found on Polymarket")

    def _clob_call(self, live_server, method, params):
        """Call a CLOB endpoint; skip on 404 (market may be closed/delisted)."""
        try:
            return live_server._cli(
                ["PolymarketClobService", method, "-r", json.dumps(params)]
            )
        except Exception as exc:
            if "404" in str(exc):
                pytest.skip(f"CLOB {method} returned 404 (market may be closed)")
            raise

    def test_get_orderbook(self, live_server, active_market_info):
        result = self._clob_call(
            live_server, "GetOrderbook", {"token_id": active_market_info["token_id"]}
        )
        assert "data" in result
        ob = result["data"]
        assert "bids" in ob or "asks" in ob
        assert "market" in ob or "asset_id" in ob

    def test_get_price(self, live_server, active_market_info):
        result = self._clob_call(
            live_server, "GetPrice", {"token_id": active_market_info["token_id"], "side": "BUY"}
        )
        assert "data" in result
        assert "price" in result["data"]

    def test_get_midpoint(self, live_server, active_market_info):
        result = self._clob_call(
            live_server, "GetMidpoint", {"token_id": active_market_info["token_id"]}
        )
        assert "data" in result
        assert "mid" in result["data"]

    def test_get_spread(self, live_server, active_market_info):
        result = self._clob_call(
            live_server, "GetSpread", {"token_id": active_market_info["token_id"]}
        )
        assert "data" in result
        assert "spread" in result["data"]

    def test_get_price_history(self, live_server, active_market_info):
        condition_id = active_market_info.get("condition_id")
        if not condition_id:
            pytest.skip("no condition_id available for active token")

        result = self._clob_call(
            live_server,
            "GetPriceHistory",
            {"market": condition_id, "interval": "1d", "fidelity": 10},
        )
        assert "data" in result
        # Closed markets may return empty data
        if result["data"]:
            assert "history" in result["data"]


# --- Data API: leaderboard ---


class TestLiveData:
    def test_get_leaderboard(self, live_server):
        result = live_server._cli(
            [
                "PolymarketDataService",
                "GetLeaderboard",
                "-r",
                json.dumps({"interval": "max", "limit": 3, "offset": 0}),
            ]
        )
        assert "data" in result
        leaders = result["data"]
        assert isinstance(leaders, list)
        assert len(leaders) > 0
        leader = leaders[0]
        assert "pseudonym" in leader or "proxyWallet" in leader or "proxy_wallet" in leader
