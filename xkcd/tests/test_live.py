"""Live integration tests for XKCD API -- hits the real API.

Run with:
    XKCD_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) XKCD JSON API and explainxkcd endpoints.
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
    os.getenv("XKCD_RUN_LIVE_TESTS") != "1",
    reason="Set XKCD_RUN_LIVE_TESTS=1 to run live XKCD API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from xkcd_mcp.gen.xkcd.v1 import xkcd_pb2 as _pb  # noqa: F401
    from xkcd_mcp.service import XKCDService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-xkcd-live", version="0.0.1"
    )
    svc = XKCDService()
    srv.register(svc)
    yield srv
    srv.stop()


# --- Shared fixtures ---


@pytest.fixture(scope="module")
def latest_comic(live_server):
    """Fetch the latest comic once for tests that need it."""
    result = live_server._cli(["XKCDService", "GetLatest"])
    assert "comic" in result
    return result["comic"]


# --- Latest ---


class TestLiveLatest:
    def test_get_latest(self, live_server, latest_comic):
        assert latest_comic["num"] > 0
        assert latest_comic.get("title")
        assert latest_comic.get("img")
        assert latest_comic.get("alt")


# --- Get specific comic ---


class TestLiveGetComic:
    def test_get_comic_1(self, live_server):
        result = live_server._cli(
            ["XKCDService", "GetComic", "-r", '{"num": 1}']
        )
        assert "comic" in result
        comic = result["comic"]
        assert comic["num"] == 1
        assert comic.get("title")
        assert comic.get("img")

    def test_get_comic_353(self, live_server):
        """Comic 353 is the famous 'Python' comic."""
        result = live_server._cli(
            ["XKCDService", "GetComic", "-r", '{"num": 353}']
        )
        comic = result["comic"]
        assert comic["num"] == 353
        assert "Python" in comic.get("title", "")


# --- Random ---


class TestLiveRandom:
    def test_get_random(self, live_server):
        result = live_server._cli(["XKCDService", "GetRandom"])
        assert "comic" in result
        comic = result["comic"]
        assert comic["num"] > 0
        assert comic.get("title")
        assert comic.get("img")


# --- Range ---


class TestLiveRange:
    def test_get_range(self, live_server):
        result = live_server._cli(
            ["XKCDService", "GetRange", "-r", '{"start_num": 1, "end_num": 3}']
        )
        assert "comics" in result
        comics = result["comics"]
        assert len(comics) == 3
        nums = [c["num"] for c in comics]
        assert 1 in nums
        assert 2 in nums
        assert 3 in nums


# --- Search by title ---


class TestLiveSearchByTitle:
    def test_search_by_title(self, live_server):
        result = live_server._cli(
            ["XKCDService", "SearchByTitle", "-r", json.dumps({"query": "Python", "search_count": 500})]
        )
        assert "comics" in result
        comics = result["comics"]
        assert len(comics) > 0
        # At least one result should have "Python" in the title
        assert any("Python" in c.get("title", "").lower() or "python" in c.get("title", "").lower() for c in comics)


# --- Explanation ---


class TestLiveExplanation:
    def test_get_explanation(self, live_server):
        result = live_server._cli(
            ["XKCDService", "GetExplanation", "-r", '{"num": 353}']
        )
        assert result.get("num") == 353
        assert result.get("title")
        assert result.get("explanation")
        assert len(result["explanation"]) > 50
        assert result.get("url")


# --- Comic count ---


class TestLiveComicCount:
    def test_get_comic_count(self, live_server):
        result = live_server._cli(["XKCDService", "GetComicCount"])
        count = result.get("count")
        assert count is not None
        assert count > 2000  # There are well over 2000 XKCD comics


# --- Multiple ---


class TestLiveMultiple:
    def test_get_multiple(self, live_server):
        result = live_server._cli(
            ["XKCDService", "GetMultiple", "-r", '{"nums": [1, 353, 927]}']
        )
        assert "comics" in result
        comics = result["comics"]
        assert len(comics) == 3
        nums = {c["num"] for c in comics}
        assert nums == {1, 353, 927}


# --- Recent ---


class TestLiveRecent:
    def test_get_recent(self, live_server):
        result = live_server._cli(
            ["XKCDService", "GetRecent", "-r", '{"count": 3}']
        )
        assert "comics" in result
        comics = result["comics"]
        assert len(comics) == 3
        # Should be in descending order
        assert comics[0]["num"] > comics[1]["num"]
        assert comics[1]["num"] > comics[2]["num"]


# --- By date ---


class TestLiveByDate:
    def test_get_by_date(self, live_server):
        # 2024 January should have some comics
        result = live_server._cli(
            ["XKCDService", "GetByDate", "-r", json.dumps({"year": 2024, "month": 1, "search_count": 500})]
        )
        assert "comics" in result
        comics = result["comics"]
        assert len(comics) > 0
        for comic in comics:
            assert comic.get("year") == "2024"
            assert comic.get("month") in ("1", "01")
