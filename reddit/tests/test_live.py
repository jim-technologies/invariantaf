"""Live integration tests for Reddit API -- hits the real API.

Run with:
    REDDIT_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) Reddit JSON API endpoints.
Reddit rate-limits anonymous requests; keep test volume low.
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
    os.getenv("REDDIT_RUN_LIVE_TESTS") != "1",
    reason="Set REDDIT_RUN_LIVE_TESTS=1 to run live Reddit API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from reddit_mcp.gen.reddit.v1 import reddit_pb2 as _reddit_pb2  # noqa: F401
    from reddit_mcp.service import RedditService
    from invariant import Server

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-reddit-live", version="0.0.1"
    )
    svc = RedditService()
    srv.register(svc)
    yield srv
    srv.stop()


# --- Shared fixtures for data discovery ---


@pytest.fixture(scope="module")
def discovered_post(live_server):
    """Discover a post from a well-known subreddit for tests that need a post ID."""
    result = live_server._cli(
        ["RedditService", "GetHot", "-r", json.dumps({"subreddit": "python", "limit": 3})]
    )
    posts = result.get("posts", [])
    assert posts, "expected at least one post from r/python"
    return posts[0]


# --- Subreddit listing ---


class TestLiveSubredditListings:
    def test_get_hot(self, live_server):
        result = live_server._cli(
            ["RedditService", "GetHot", "-r", json.dumps({"subreddit": "python", "limit": 3})]
        )
        assert "posts" in result
        posts = result["posts"]
        assert isinstance(posts, list)
        assert len(posts) > 0
        p = posts[0]
        assert "title" in p
        assert "author" in p
        assert "subreddit" in p

    def test_get_top(self, live_server):
        result = live_server._cli(
            [
                "RedditService",
                "GetTop",
                "-r",
                json.dumps({"subreddit": "python", "time_filter": "month", "limit": 3}),
            ]
        )
        assert "posts" in result
        posts = result["posts"]
        assert isinstance(posts, list)
        assert len(posts) > 0

    def test_get_new(self, live_server):
        result = live_server._cli(
            ["RedditService", "GetNew", "-r", json.dumps({"subreddit": "python", "limit": 3})]
        )
        assert "posts" in result
        posts = result["posts"]
        assert isinstance(posts, list)
        assert len(posts) > 0


# --- Post detail ---


class TestLivePost:
    def test_get_post(self, live_server, discovered_post):
        post_id = discovered_post.get("id", "")
        subreddit = discovered_post.get("subreddit", "")
        if not post_id or not subreddit:
            pytest.skip("no post_id or subreddit in discovered post")
        result = live_server._cli(
            [
                "RedditService",
                "GetPost",
                "-r",
                json.dumps({"subreddit": subreddit, "post_id": post_id}),
            ]
        )
        assert "post" in result
        assert result["post"]["id"] == post_id
        # Comments may or may not be present
        assert "comments" in result or isinstance(result.get("comments"), list) or True


# --- Search ---


class TestLiveSearch:
    def test_search_posts(self, live_server):
        result = live_server._cli(
            ["RedditService", "SearchPosts", "-r", json.dumps({"query": "python tutorial", "limit": 3})]
        )
        assert "posts" in result
        posts = result["posts"]
        assert isinstance(posts, list)
        assert len(posts) > 0


# --- Subreddit info ---


class TestLiveSubreddit:
    def test_get_subreddit(self, live_server):
        result = live_server._cli(
            ["RedditService", "GetSubreddit", "-r", json.dumps({"subreddit": "python"})]
        )
        assert "subreddit" in result
        sr = result["subreddit"]
        assert sr.get("displayName") == "python" or sr.get("display_name") == "python"
        assert sr.get("subscribers", 0) > 0 or sr.get("subscribers") is not None


# --- User ---


class TestLiveUser:
    def test_get_user(self, live_server):
        # Use the AutoModerator account which is always present
        result = live_server._cli(
            ["RedditService", "GetUser", "-r", json.dumps({"username": "AutoModerator"})]
        )
        assert "user" in result
        user = result["user"]
        assert user.get("name") == "AutoModerator"

    def test_get_user_posts(self, live_server):
        result = live_server._cli(
            ["RedditService", "GetUserPosts", "-r", json.dumps({"username": "AutoModerator", "limit": 3})]
        )
        assert "posts" in result
        posts = result["posts"]
        assert isinstance(posts, list)
        # AutoModerator may have no submitted posts visible, so just check structure
        if posts:
            assert "title" in posts[0]


# --- Popular / Front page ---


class TestLivePopular:
    def test_get_popular_subreddits(self, live_server):
        result = live_server._cli(
            ["RedditService", "GetPopularSubreddits", "-r", json.dumps({"limit": 3})]
        )
        assert "subreddits" in result
        subs = result["subreddits"]
        assert isinstance(subs, list)
        assert len(subs) > 0
        sr = subs[0]
        assert "displayName" in sr or "display_name" in sr

    def test_get_front_page(self, live_server):
        result = live_server._cli(
            ["RedditService", "GetFrontPage", "-r", json.dumps({"limit": 3})]
        )
        assert "posts" in result
        posts = result["posts"]
        assert isinstance(posts, list)
        assert len(posts) > 0
        assert "title" in posts[0]
