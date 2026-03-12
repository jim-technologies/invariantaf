"""Live integration tests for Hacker News API -- hits the real API.

Run with:
    HACKERNEWS_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) Hacker News Firebase API endpoints.
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
    os.getenv("HACKERNEWS_RUN_LIVE_TESTS") != "1",
    reason="Set HACKERNEWS_RUN_LIVE_TESTS=1 to run live Hacker News API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from hackernews_mcp.gen.hackernews.v1 import hackernews_pb2 as _pb  # noqa: F401
    from hackernews_mcp.service import HackerNewsService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-hackernews-live", version="0.0.1"
    )
    svc = HackerNewsService()
    srv.register(svc)
    yield srv
    srv.stop()


# --- Shared fixtures for data discovery ---


@pytest.fixture(scope="module")
def top_story(live_server):
    """Fetch one top story for tests that need a story ID."""
    result = live_server._cli(
        ["HackerNewsService", "GetTopStories", "-r", '{"limit": 1}']
    )
    items = result.get("items", [])
    assert items, "expected at least one top story"
    return items[0]


# --- Story listing endpoints ---


class TestLiveStories:
    def test_get_top_stories(self, live_server):
        result = live_server._cli(
            ["HackerNewsService", "GetTopStories", "-r", '{"limit": 3}']
        )
        assert "items" in result
        items = result["items"]
        assert isinstance(items, list)
        assert len(items) > 0
        item = items[0]
        assert "id" in item
        assert "title" in item or "type" in item

    def test_get_new_stories(self, live_server):
        result = live_server._cli(
            ["HackerNewsService", "GetNewStories", "-r", '{"limit": 3}']
        )
        assert "items" in result
        items = result["items"]
        assert isinstance(items, list)
        assert len(items) > 0

    def test_get_best_stories(self, live_server):
        result = live_server._cli(
            ["HackerNewsService", "GetBestStories", "-r", '{"limit": 3}']
        )
        assert "items" in result
        items = result["items"]
        assert isinstance(items, list)
        assert len(items) > 0

    def test_get_ask_stories(self, live_server):
        result = live_server._cli(
            ["HackerNewsService", "GetAskStories", "-r", '{"limit": 3}']
        )
        assert "items" in result
        items = result["items"]
        assert isinstance(items, list)
        assert len(items) > 0

    def test_get_show_stories(self, live_server):
        result = live_server._cli(
            ["HackerNewsService", "GetShowStories", "-r", '{"limit": 3}']
        )
        assert "items" in result
        items = result["items"]
        assert isinstance(items, list)
        assert len(items) > 0

    def test_get_job_stories(self, live_server):
        result = live_server._cli(
            ["HackerNewsService", "GetJobStories", "-r", '{"limit": 3}']
        )
        assert "items" in result
        items = result["items"]
        assert isinstance(items, list)
        # Jobs may be empty at times
        if not items:
            pytest.skip("No job stories currently available")


# --- Item detail ---


class TestLiveItem:
    def test_get_item_by_id(self, live_server, top_story):
        item_id = top_story["id"]
        result = live_server._cli(
            ["HackerNewsService", "GetItem", "-r", json.dumps({"id": item_id})]
        )
        assert "item" in result
        assert result["item"]["id"] == item_id

    def test_get_item_has_expected_fields(self, live_server, top_story):
        item_id = top_story["id"]
        result = live_server._cli(
            ["HackerNewsService", "GetItem", "-r", json.dumps({"id": item_id})]
        )
        item = result["item"]
        assert "type" in item
        assert "by" in item or item.get("deleted")


# --- User ---


class TestLiveUser:
    def test_get_user(self, live_server):
        # pg (Paul Graham) is a well-known stable user on HN
        result = live_server._cli(
            ["HackerNewsService", "GetUser", "-r", '{"id": "pg"}']
        )
        assert "user" in result
        user = result["user"]
        assert user["id"] == "pg"
        assert "karma" in user
        assert user["karma"] > 0

    def test_get_user_from_story(self, live_server, top_story):
        author = top_story.get("by")
        if not author:
            pytest.skip("Top story has no author (deleted?)")
        result = live_server._cli(
            ["HackerNewsService", "GetUser", "-r", json.dumps({"id": author})]
        )
        assert "user" in result
        assert result["user"]["id"] == author


# --- Comments ---


class TestLiveComments:
    def test_get_comments(self, live_server, top_story):
        item_id = top_story["id"]
        kids = top_story.get("kids", [])
        if not kids:
            pytest.skip("Top story has no comments")
        result = live_server._cli(
            [
                "HackerNewsService",
                "GetComments",
                "-r",
                json.dumps({"story_id": item_id, "depth": 1, "limit": 5}),
            ]
        )
        assert "comments" in result
        comments = result["comments"]
        assert isinstance(comments, list)
        assert len(comments) > 0
        comment = comments[0]
        assert "type" in comment
        assert comment["type"] == "comment"


# --- Max item ---


class TestLiveMaxItem:
    def test_get_max_item(self, live_server):
        result = live_server._cli(["HackerNewsService", "GetMaxItem"])
        val = result.get("maxId") or result.get("max_id")
        assert val is not None
        assert int(val) > 0
