"""Live integration tests for Wikipedia API -- hits the real API.

Run with:
    WIKIPEDIA_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) Wikipedia REST and Action API endpoints.
No API key or authentication is required.
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
    os.getenv("WIKIPEDIA_RUN_LIVE_TESTS") != "1",
    reason="Set WIKIPEDIA_RUN_LIVE_TESTS=1 to run live Wikipedia API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from wikipedia_mcp.gen.wikipedia.v1 import wikipedia_pb2 as _pb  # noqa: F401
    from wikipedia_mcp.service import WikipediaService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-wikipedia-live", version="0.0.1"
    )
    svc = WikipediaService()
    srv.register(svc)
    yield srv
    srv.stop()


# --- Search ---


class TestLiveSearch:
    def test_search(self, live_server):
        result = live_server._cli(
            ["WikipediaService", "Search", "-r", json.dumps({"query": "quantum computing", "limit": 5})]
        )
        assert "results" in result
        results = result["results"]
        assert isinstance(results, list)
        assert len(results) > 0
        r = results[0]
        assert "title" in r
        assert "snippet" in r
        val = result.get("totalHits") or result.get("total_hits")
        assert val is not None
        assert int(val) > 0

    def test_search_returns_page_ids(self, live_server):
        result = live_server._cli(
            ["WikipediaService", "Search", "-r", json.dumps({"query": "Python programming", "limit": 3})]
        )
        results = result["results"]
        assert len(results) > 0
        for r in results:
            page_id = r.get("pageId") or r.get("page_id")
            assert page_id is not None
            assert int(page_id) > 0


# --- Page summary ---


class TestLiveGetPage:
    def test_get_page(self, live_server):
        result = live_server._cli(
            ["WikipediaService", "GetPage", "-r", '{"title": "Albert_Einstein"}']
        )
        assert result.get("title") == "Albert Einstein"
        assert result.get("extract")
        assert len(result["extract"]) > 50

    def test_get_page_has_metadata(self, live_server):
        result = live_server._cli(
            ["WikipediaService", "GetPage", "-r", '{"title": "Python_(programming_language)"}']
        )
        assert "Python" in result.get("title", "")
        assert result.get("description") or result.get("extract")
        page_id = result.get("pageId") or result.get("page_id")
        assert page_id is not None
        assert int(page_id) > 0


# --- Full page ---


class TestLiveGetFullPage:
    def test_get_full_page(self, live_server):
        result = live_server._cli(
            ["WikipediaService", "GetFullPage", "-r", '{"title": "Albert_Einstein"}']
        )
        assert result.get("title") == "Albert Einstein"
        assert result.get("content")
        # Full page content should be substantial
        assert len(result["content"]) > 1000


# --- Random ---


class TestLiveGetRandom:
    def test_get_random(self, live_server):
        result = live_server._cli(["WikipediaService", "GetRandom"])
        assert "pages" in result
        pages = result["pages"]
        assert isinstance(pages, list)
        assert len(pages) >= 1
        page = pages[0]
        assert "title" in page
        assert page["title"]  # not empty

    def test_get_random_multiple(self, live_server):
        result = live_server._cli(
            ["WikipediaService", "GetRandom", "-r", '{"count": 3}']
        )
        pages = result["pages"]
        assert len(pages) == 3


# --- On this day ---


class TestLiveGetOnThisDay:
    def test_get_on_this_day(self, live_server):
        result = live_server._cli(
            ["WikipediaService", "GetOnThisDay", "-r", '{"month": 7, "day": 4}']
        )
        assert "events" in result
        events = result["events"]
        assert isinstance(events, list)
        assert len(events) > 0
        event = events[0]
        assert "year" in event
        assert "text" in event


# --- Most read ---


class TestLiveGetMostRead:
    def test_get_most_read(self, live_server):
        # Use a date that is safely in the past
        result = live_server._cli(
            ["WikipediaService", "GetMostRead", "-r", '{"year": 2025, "month": 1, "day": 15}']
        )
        assert "articles" in result
        articles = result["articles"]
        assert isinstance(articles, list)
        assert len(articles) > 0
        article = articles[0]
        assert "title" in article
        assert "views" in article
        assert int(article["views"]) > 0


# --- Languages ---


class TestLiveGetLanguages:
    def test_get_languages(self, live_server):
        result = live_server._cli(
            ["WikipediaService", "GetLanguages", "-r", '{"title": "Albert_Einstein"}']
        )
        assert "languages" in result
        languages = result["languages"]
        assert isinstance(languages, list)
        assert len(languages) > 10  # Einstein article exists in many languages
        lang = languages[0]
        assert "lang" in lang
        assert "title" in lang


# --- Categories ---


class TestLiveGetCategories:
    def test_get_categories(self, live_server):
        result = live_server._cli(
            ["WikipediaService", "GetCategories", "-r", '{"title": "Albert_Einstein"}']
        )
        assert "categories" in result
        categories = result["categories"]
        assert isinstance(categories, list)
        assert len(categories) > 0
        # Categories typically start with "Category:"
        assert any("Category:" in c for c in categories)


# --- Links ---


class TestLiveGetLinks:
    def test_get_links(self, live_server):
        result = live_server._cli(
            ["WikipediaService", "GetLinks", "-r", '{"title": "Albert_Einstein"}']
        )
        assert "links" in result
        links = result["links"]
        assert isinstance(links, list)
        assert len(links) > 0


# --- Images ---


class TestLiveGetImages:
    def test_get_images(self, live_server):
        result = live_server._cli(
            ["WikipediaService", "GetImages", "-r", '{"title": "Albert_Einstein"}']
        )
        assert "images" in result
        images = result["images"]
        assert isinstance(images, list)
        assert len(images) > 0
        # Images are typically "File:..." filenames
        assert any("File:" in img or "file:" in img.lower() for img in images)
