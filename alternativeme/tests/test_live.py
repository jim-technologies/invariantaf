"""Live integration tests for Alternative.me API -- hits the real API.

Run with:
    ALTERNATIVEME_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) endpoints.
No API keys or credentials needed.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_BASE_URL = "https://api.alternative.me"

pytestmark = pytest.mark.skipif(
    os.getenv("ALTERNATIVEME_RUN_LIVE_TESTS") != "1",
    reason="Set ALTERNATIVEME_RUN_LIVE_TESTS=1 to run live Alternative.me API tests",
)


def _cli_or_skip(live_server, service, method, params=None):
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
        if any(code in msg for code in ("429", "500", "502", "503", "Timeout", "timed out")):
            pytest.skip(f"{method}: {msg[:120]}")
        raise


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from alternativeme_mcp.gen.alternativeme.v1 import alternativeme_pb2 as _alternativeme_pb2  # noqa: F401
    from alternativeme_mcp.service import AlternativeMeService

    base_url = (os.getenv("ALTERNATIVEME_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-alternativeme-live", version="0.0.1"
    )
    servicer = AlternativeMeService(base_url=base_url)
    srv.register(servicer, service_name="alternativeme.v1.AlternativeMeService")
    yield srv
    srv.stop()


# --- GetFearGreedIndex ---


class TestLiveGetFearGreedIndex:
    def test_current_value(self, live_server):
        result = _cli_or_skip(
            live_server, "AlternativeMeService", "GetFearGreedIndex",
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) >= 1
        entry = data[0]
        assert "value" in entry
        val = int(entry["value"])
        assert 0 <= val <= 100
        assert "value_classification" in entry
        assert entry["value_classification"] in (
            "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed",
        )

    def test_historical_values(self, live_server):
        result = _cli_or_skip(
            live_server, "AlternativeMeService", "GetFearGreedIndex",
            {"limit": 5},
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) == 5
        for entry in data:
            val = int(entry["value"])
            assert 0 <= val <= 100


# --- GetGlobalMarketData ---


class TestLiveGetGlobalMarketData:
    def test_top_coins(self, live_server):
        result = _cli_or_skip(
            live_server, "AlternativeMeService", "GetGlobalMarketData",
            {"limit": 5},
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) >= 1
        coin = data[0]
        assert "name" in coin
        assert "symbol" in coin
        assert "price_usd" in coin
        price = float(coin["price_usd"])
        assert price > 0


# --- GetCoinData ---


class TestLiveGetCoinData:
    def test_get_bitcoin(self, live_server):
        result = _cli_or_skip(
            live_server, "AlternativeMeService", "GetCoinData",
            {"id": "1"},
        )
        assert "data" in result
        data = result["data"]
        assert data["name"] == "Bitcoin"
        assert data["symbol"] == "BTC"
        assert float(data["price_usd"]) > 0

    def test_get_ethereum(self, live_server):
        result = _cli_or_skip(
            live_server, "AlternativeMeService", "GetCoinData",
            {"id": "1027"},
        )
        assert "data" in result
        data = result["data"]
        assert data["name"] == "Ethereum"
        assert data["symbol"] == "ETH"
        assert float(data["price_usd"]) > 0


# --- GetListings ---


class TestLiveGetListings:
    def test_get_listings(self, live_server):
        result = _cli_or_skip(
            live_server, "AlternativeMeService", "GetListings",
            {"limit": 10},
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) >= 1
        listing = data[0]
        assert "name" in listing
        assert "symbol" in listing
        assert "id" in listing
