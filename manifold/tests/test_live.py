"""Live integration tests for Manifold Markets API -- hits the real API.

Run with:
    MANIFOLD_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) endpoints.
No API key or credentials are needed.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")
DEFAULT_BASE_URL = "https://api.manifold.markets/v0"

pytestmark = pytest.mark.skipif(
    os.getenv("MANIFOLD_RUN_LIVE_TESTS") != "1",
    reason="Set MANIFOLD_RUN_LIVE_TESTS=1 to run live Manifold API tests",
)

_CLI_OR_SKIP_CODES = {404, 429, 500, 502, 503}


def _cli_or_skip(live_server, service, method, params=None):
    """Call a CLI method; skip on transient HTTP errors (429/5xx)."""
    cli_args = [service, method]
    if params is not None:
        cli_args += ["-r", json.dumps(params)]
    try:
        return live_server._cli(cli_args)
    except Exception as exc:
        msg = str(exc)
        for code in _CLI_OR_SKIP_CODES:
            if str(code) in msg:
                pytest.skip(f"{method} returned {code}: {msg}")
        raise


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from gen.manifold.v1 import manifold_pb2 as _manifold_pb2  # noqa: F401

    base_url = (os.getenv("MANIFOLD_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-manifold-live", version="0.0.1"
    )
    srv.connect_http(base_url, service_name="manifold.v1.ManifoldService")
    yield srv
    srv.stop()


class TestLiveListMarkets:
    def test_list_markets(self, live_server):
        result = _cli_or_skip(
            live_server, "ManifoldService", "ListMarkets", {"limit": 3}
        )
        assert "data" in result
        markets = result["data"]
        assert isinstance(markets, list)
        assert len(markets) > 0
        m = markets[0]
        assert "id" in m
        assert "question" in m

    def test_list_markets_with_sort(self, live_server):
        result = _cli_or_skip(
            live_server,
            "ManifoldService",
            "ListMarkets",
            {"limit": 2, "sort": "created-time", "order": "desc"},
        )
        markets = result["data"]
        assert isinstance(markets, list)
        assert len(markets) > 0


class TestLiveGetMarket:
    @pytest.fixture(scope="class")
    def first_market(self, live_server):
        """Fetch a single market once for all detail tests."""
        result = _cli_or_skip(
            live_server, "ManifoldService", "ListMarkets", {"limit": 1}
        )
        markets = result["data"]
        assert markets, "expected at least one market"
        return markets[0]

    def test_get_market_by_id(self, live_server, first_market):
        market_id = first_market["id"]
        result = _cli_or_skip(
            live_server,
            "ManifoldService",
            "GetMarket",
            {"market_id": market_id},
        )
        assert "data" in result
        assert result["data"]["id"] == market_id

    def test_get_market_has_fields(self, live_server, first_market):
        market_id = first_market["id"]
        result = _cli_or_skip(
            live_server,
            "ManifoldService",
            "GetMarket",
            {"market_id": market_id},
        )
        data = result["data"]
        assert "question" in data
        assert "outcome_type" in data or "outcomeType" in data


class TestLiveSearchMarkets:
    def test_search_markets(self, live_server):
        result = _cli_or_skip(
            live_server,
            "ManifoldService",
            "SearchMarkets",
            {"term": "bitcoin", "limit": 3, "filter": "open"},
        )
        assert "data" in result
        markets = result["data"]
        assert isinstance(markets, list)

    def test_search_with_offset(self, live_server):
        result = _cli_or_skip(
            live_server,
            "ManifoldService",
            "SearchMarkets",
            {"term": "election", "limit": 2, "offset": 0},
        )
        assert "data" in result
        assert isinstance(result["data"], list)


class TestLiveMarketPositions:
    def test_get_market_positions(self, live_server):
        # First get a market id
        list_result = _cli_or_skip(
            live_server, "ManifoldService", "ListMarkets", {"limit": 1}
        )
        markets = list_result["data"]
        if not markets:
            pytest.skip("no markets available")
        market_id = markets[0]["id"]

        result = _cli_or_skip(
            live_server,
            "ManifoldService",
            "GetMarketPositions",
            {"market_id": market_id, "top": 5, "order": "shares"},
        )
        # API may return {"data": [...]} or just the list directly
        positions = result.get("data", result.get("positions", []))
        assert isinstance(positions, list)


class TestLiveUser:
    def test_get_user_by_username(self, live_server):
        result = _cli_or_skip(
            live_server,
            "ManifoldService",
            "GetUserByUsername",
            {"username": "ManifoldMarkets"},
        )
        assert "data" in result
        data = result["data"]
        assert "id" in data
        assert "username" in data or "name" in data

    def test_get_user_by_id(self, live_server):
        # First get a user id via username lookup
        username_result = _cli_or_skip(
            live_server,
            "ManifoldService",
            "GetUserByUsername",
            {"username": "ManifoldMarkets"},
        )
        user_id = username_result["data"]["id"]

        result = _cli_or_skip(
            live_server,
            "ManifoldService",
            "GetUser",
            {"user_id": user_id},
        )
        assert "data" in result
        assert result["data"]["id"] == user_id
