"""Live integration tests for Opinion.trade API -- hits the real API.

Run with:
    OPINION_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

Optionally set OPINION_API_KEY for authenticated endpoints.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_BASE_URL = "https://openapi.opinion.trade/openapi"

_SKIP_STATUS_CODES = {401, 403, 429, 500, 502, 503}

pytestmark = pytest.mark.skipif(
    os.getenv("OPINION_RUN_LIVE_TESTS") != "1",
    reason="Set OPINION_RUN_LIVE_TESTS=1 to run live Opinion.trade API tests",
)


def _cli_or_skip(server, service: str, method: str, params: dict | None = None):
    """Call an RPC via CLI; skip on transient/auth HTTP errors."""
    args = [service, method]
    if params:
        args += ["-r", json.dumps(params)]
    try:
        return server._cli(args)
    except Exception as exc:
        msg = str(exc)
        for code in _SKIP_STATUS_CODES:
            if str(code) in msg:
                pytest.skip(f"{method} returned {code}: {msg}")
        raise


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from gen.opinion.v1 import opinion_pb2 as _opinion_pb2  # noqa: F401

    base_url = (
        os.getenv("OPINION_BASE_URL") or DEFAULT_BASE_URL
    ).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-opinion-live", version="0.0.1"
    )

    api_key = (os.getenv("OPINION_API_KEY") or "").strip()
    if api_key:
        def provider(req):
            return {"apikey": api_key}
        srv.use_http_header_provider(provider)

    srv.connect_http(base_url, service_name="opinion.v1.OpinionService")
    yield srv
    srv.stop()


class TestLiveMarkets:
    def test_list_markets(self, live_server):
        result = _cli_or_skip(
            live_server,
            "OpinionService",
            "ListMarkets",
            {"page": 1, "limit": 5},
        )
        assert "data" in result
        data = result["data"]
        assert "total" in data or "list" in data
        if "list" in data:
            assert isinstance(data["list"], list)
            assert len(data["list"]) > 0

    def test_list_markets_with_status(self, live_server):
        result = _cli_or_skip(
            live_server,
            "OpinionService",
            "ListMarkets",
            {"page": 1, "limit": 3, "status": "activated"},
        )
        assert "data" in result

    @pytest.fixture(scope="class")
    def first_market(self, live_server):
        """Fetch the first market for downstream detail tests."""
        result = _cli_or_skip(
            live_server,
            "OpinionService",
            "ListMarkets",
            {"page": 1, "limit": 1},
        )
        markets = result.get("data", {}).get("list", [])
        if not markets:
            pytest.skip("no markets returned from ListMarkets")
        return markets[0]

    def test_get_market(self, live_server, first_market):
        market_id = first_market.get("market_id") or first_market.get("marketId")
        if not market_id:
            pytest.skip("no market_id in first market")
        result = _cli_or_skip(
            live_server,
            "OpinionService",
            "GetMarket",
            {"market_id": market_id},
        )
        assert "data" in result
        assert result["data"].get("market_id") == market_id or result["data"].get("marketId") == market_id

    def test_get_market_by_slug(self, live_server, first_market):
        slug = first_market.get("slug")
        if not slug:
            pytest.skip("no slug in first market")
        result = _cli_or_skip(
            live_server,
            "OpinionService",
            "GetMarketBySlug",
            {"slug": slug},
        )
        assert "data" in result


class TestLiveTokens:
    @pytest.fixture(scope="class")
    def active_token_id(self, live_server):
        """Find a token_id from an active market."""
        result = _cli_or_skip(
            live_server,
            "OpinionService",
            "ListMarkets",
            {"page": 1, "limit": 10, "status": "activated"},
        )
        markets = result.get("data", {}).get("list", [])
        for mkt in markets:
            tokens = mkt.get("tokens", [])
            if tokens:
                tok = tokens[0]
                tid = tok.get("token_id") or tok.get("tokenId")
                if tid:
                    return tid
        pytest.skip("no active market with tokens found")

    def test_get_latest_price(self, live_server, active_token_id):
        result = _cli_or_skip(
            live_server,
            "OpinionService",
            "GetLatestPrice",
            {"token_id": active_token_id},
        )
        assert "data" in result

    def test_get_orderbook(self, live_server, active_token_id):
        result = _cli_or_skip(
            live_server,
            "OpinionService",
            "GetOrderbook",
            {"token_id": active_token_id},
        )
        assert "data" in result
        ob = result["data"]
        assert "bids" in ob or "asks" in ob

    def test_get_price_history(self, live_server, active_token_id):
        result = _cli_or_skip(
            live_server,
            "OpinionService",
            "GetPriceHistory",
            {"token_id": active_token_id, "interval": "1d"},
        )
        assert "data" in result


class TestLiveQuoteTokens:
    def test_list_quote_tokens(self, live_server):
        result = _cli_or_skip(
            live_server,
            "OpinionService",
            "ListQuoteTokens",
        )
        assert "data" in result
        assert isinstance(result["data"], list)
