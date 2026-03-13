"""Live integration tests for Wikimedia API -- hits the real API.

Run with:
    WIKIMEDIA_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

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

DEFAULT_BASE_URL = "https://wikimedia.org/api/rest_v1"

pytestmark = pytest.mark.skipif(
    os.getenv("WIKIMEDIA_RUN_LIVE_TESTS") != "1",
    reason="Set WIKIMEDIA_RUN_LIVE_TESTS=1 to run live Wikimedia API tests",
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
    from wikimedia_mcp.gen.wikimedia.v1 import wikimedia_pb2 as _wikimedia_pb2  # noqa: F401
    from wikimedia_mcp.service import WikimediaService

    base_url = (os.getenv("WIKIMEDIA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-wikimedia-live", version="0.0.1"
    )
    servicer = WikimediaService(base_url=base_url)
    srv.register(servicer, service_name="wikimedia.v1.WikimediaService")
    yield srv
    srv.stop()


# --- GetPageviews ---


class TestLiveGetPageviews:
    def test_bitcoin_pageviews(self, live_server):
        result = _cli_or_skip(
            live_server, "WikimediaService", "GetPageviews",
            {"article": "Bitcoin", "start": "20250101", "end": "20250107"},
        )
        assert "items" in result
        items = result["items"]
        assert isinstance(items, list)
        assert len(items) > 0
        item = items[0]
        assert item["article"] == "Bitcoin"
        assert int(item["views"]) > 0
        assert item["project"] == "en.wikipedia"

    def test_ethereum_pageviews(self, live_server):
        result = _cli_or_skip(
            live_server, "WikimediaService", "GetPageviews",
            {"article": "Ethereum", "start": "20250101", "end": "20250107"},
        )
        assert "items" in result
        items = result["items"]
        assert len(items) > 0
        assert items[0]["article"] == "Ethereum"
        assert int(items[0]["views"]) > 0

    def test_donald_trump_pageviews(self, live_server):
        result = _cli_or_skip(
            live_server, "WikimediaService", "GetPageviews",
            {"article": "Donald_Trump", "start": "20250101", "end": "20250107"},
        )
        assert "items" in result
        items = result["items"]
        assert len(items) > 0
        assert items[0]["article"] == "Donald_Trump"
        assert int(items[0]["views"]) > 0

    def test_federal_reserve_pageviews(self, live_server):
        result = _cli_or_skip(
            live_server, "WikimediaService", "GetPageviews",
            {"article": "Federal_Reserve", "start": "20250101", "end": "20250107"},
        )
        assert "items" in result
        items = result["items"]
        assert len(items) > 0
        assert items[0]["article"] == "Federal_Reserve"
        assert int(items[0]["views"]) > 0


# --- GetTopPages ---


class TestLiveGetTopPages:
    def test_top_pages(self, live_server):
        result = _cli_or_skip(
            live_server, "WikimediaService", "GetTopPages",
            {"year": "2025", "month": "01", "day": "15"},
        )
        assert "articles" in result
        articles = result["articles"]
        assert isinstance(articles, list)
        assert len(articles) > 0
        assert int(articles[0]["views"]) > 0
        assert int(articles[0]["rank"]) == 1


# --- GetAggregatePageviews ---


class TestLiveGetAggregatePageviews:
    def test_aggregate_pageviews(self, live_server):
        result = _cli_or_skip(
            live_server, "WikimediaService", "GetAggregatePageviews",
            {"start": "20250101", "end": "20250107"},
        )
        assert "items" in result
        items = result["items"]
        assert isinstance(items, list)
        assert len(items) > 0
        assert int(items[0]["views"]) > 0
        assert items[0]["project"] == "en.wikipedia"


# --- GetMostViewed ---


class TestLiveGetMostViewed:
    def test_most_viewed_month(self, live_server):
        result = _cli_or_skip(
            live_server, "WikimediaService", "GetMostViewed",
            {"year": "2025", "month": "01"},
        )
        assert "articles" in result
        articles = result["articles"]
        assert isinstance(articles, list)
        assert len(articles) > 0
        assert int(articles[0]["views"]) > 0
        assert int(articles[0]["rank"]) == 1


# --- GetUniqueDevices ---


class TestLiveGetUniqueDevices:
    def test_unique_devices(self, live_server):
        result = _cli_or_skip(
            live_server, "WikimediaService", "GetUniqueDevices",
            {"start": "20250101", "end": "20250107"},
        )
        assert "items" in result
        items = result["items"]
        assert isinstance(items, list)
        assert len(items) > 0
        assert int(items[0]["devices"]) > 0
        assert items[0]["project"] == "en.wikipedia"
