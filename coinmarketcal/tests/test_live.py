"""Live integration tests for CoinMarketCal API -- hits the real API.

Run with:
    COINMARKETCAL_RUN_LIVE_TESTS=1 COINMARKETCAL_API_KEY=<key> uv run python -m pytest tests/test_live.py -v

Requires a valid CoinMarketCal API key.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_BASE_URL = "https://developers.coinmarketcal.com/v1"

pytestmark = pytest.mark.skipif(
    os.getenv("COINMARKETCAL_RUN_LIVE_TESTS") != "1",
    reason="Set COINMARKETCAL_RUN_LIVE_TESTS=1 and COINMARKETCAL_API_KEY to run live tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    """Call a CLI method; skip on transient errors."""
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
    from coinmarketcal_mcp.gen.coinmarketcal.v1 import coinmarketcal_pb2 as _coinmarketcal_pb2  # noqa: F401
    from coinmarketcal_mcp.service import CoinMarketCalService

    api_key = (os.getenv("COINMARKETCAL_API_KEY") or "").strip()
    base_url = (os.getenv("COINMARKETCAL_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-coinmarketcal-live", version="0.0.1"
    )
    servicer = CoinMarketCalService(api_key=api_key, base_url=base_url)
    srv.register(servicer, service_name="coinmarketcal.v1.CoinMarketCalService")
    yield srv
    srv.stop()


# --- ListEvents ---


class TestLiveListEvents:
    def test_list_events_default(self, live_server):
        result = _cli_or_skip(
            live_server, "CoinMarketCalService", "ListEvents",
        )
        assert "events" in result
        events = result["events"]
        assert isinstance(events, list)
        assert len(events) > 0
        ev = events[0]
        assert "title" in ev
        assert "dateEvent" in ev or "date_event" in ev

    def test_list_events_with_page(self, live_server):
        result = _cli_or_skip(
            live_server, "CoinMarketCalService", "ListEvents",
            {"max": 5, "page": 1},
        )
        assert "events" in result
        events = result["events"]
        assert isinstance(events, list)
        assert len(events) <= 5


# --- ListCategories ---


class TestLiveListCategories:
    def test_list_categories(self, live_server):
        result = _cli_or_skip(
            live_server, "CoinMarketCalService", "ListCategories",
        )
        assert "categories" in result
        categories = result["categories"]
        assert isinstance(categories, list)
        assert len(categories) > 0
        cat = categories[0]
        assert "id" in cat
        assert "name" in cat


# --- ListCoins ---


class TestLiveListCoins:
    def test_list_coins(self, live_server):
        result = _cli_or_skip(
            live_server, "CoinMarketCalService", "ListCoins",
        )
        assert "coins" in result
        coins = result["coins"]
        assert isinstance(coins, list)
        assert len(coins) > 0
        coin = coins[0]
        assert "name" in coin
        assert "symbol" in coin
