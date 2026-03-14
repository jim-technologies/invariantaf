"""Live integration tests for Brave Search API -- hits the real API.

Run with:
    BRAVE_RUN_LIVE_TESTS=1 BRAVE_API_KEY=<key> uv run python -m pytest tests/test_live.py -v

Requires a valid BRAVE_API_KEY.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_BASE_URL = "https://api.search.brave.com/res/v1"

pytestmark = pytest.mark.skipif(
    os.getenv("BRAVE_RUN_LIVE_TESTS") != "1" or not os.getenv("BRAVE_API_KEY"),
    reason="Set BRAVE_RUN_LIVE_TESTS=1 and BRAVE_API_KEY to run live Brave Search API tests",
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
    from bravesearch_mcp.gen.bravesearch.v1 import bravesearch_pb2 as _bravesearch_pb2  # noqa: F401
    from bravesearch_mcp.service import BraveSearchService

    base_url = (os.getenv("BRAVE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    api_key = os.getenv("BRAVE_API_KEY") or ""

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-bravesearch-live", version="0.0.1"
    )
    servicer = BraveSearchService(base_url=base_url, api_key=api_key)
    srv.register(servicer, service_name="bravesearch.v1.BraveSearchService")
    yield srv
    srv.stop()


# --- WebSearch ---


class TestLiveWebSearch:
    def test_basic_search(self, live_server):
        result = _cli_or_skip(
            live_server, "BraveSearchService", "WebSearch",
            {"query": "python programming"},
        )
        assert "results" in result
        results = result["results"]
        assert isinstance(results, list)
        assert len(results) >= 1
        first = results[0]
        assert "title" in first
        assert "url" in first

    def test_search_with_count(self, live_server):
        result = _cli_or_skip(
            live_server, "BraveSearchService", "WebSearch",
            {"query": "rust programming language", "count": 3},
        )
        assert "results" in result
        results = result["results"]
        assert isinstance(results, list)
        assert len(results) <= 3


# --- NewsSearch ---


class TestLiveNewsSearch:
    def test_basic_news(self, live_server):
        result = _cli_or_skip(
            live_server, "BraveSearchService", "NewsSearch",
            {"query": "technology"},
        )
        assert "results" in result
        results = result["results"]
        assert isinstance(results, list)
        assert len(results) >= 1
        first = results[0]
        assert "title" in first
        assert "url" in first


# --- ImageSearch ---


class TestLiveImageSearch:
    def test_basic_images(self, live_server):
        result = _cli_or_skip(
            live_server, "BraveSearchService", "ImageSearch",
            {"query": "golden gate bridge"},
        )
        assert "results" in result
        results = result["results"]
        assert isinstance(results, list)
        assert len(results) >= 1
        first = results[0]
        assert "title" in first
