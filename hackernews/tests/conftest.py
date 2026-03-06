"""Shared fixtures for Hacker News MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hackernews_mcp.gen.hackernews.v1 import hackernews_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real HN Firebase API return shapes
# ---------------------------------------------------------------------------

FAKE_STORY_1 = {
    "id": 41881548,
    "type": "story",
    "by": "pg",
    "time": 1700000000,
    "title": "Hacking the attention economy",
    "url": "https://example.com/hacking-attention",
    "score": 342,
    "descendants": 187,
    "kids": [41881600, 41881601, 41881602],
}

FAKE_STORY_2 = {
    "id": 41881549,
    "type": "story",
    "by": "dang",
    "time": 1700000100,
    "title": "Show HN: A new way to build compilers",
    "url": "https://example.com/compilers",
    "score": 128,
    "descendants": 45,
    "kids": [41881700],
}

FAKE_STORY_3 = {
    "id": 41881550,
    "type": "story",
    "by": "tptacek",
    "time": 1700000200,
    "title": "Ask HN: What are you working on?",
    "text": "Curious what side projects people are building this week.",
    "score": 95,
    "descendants": 210,
    "kids": [41881800, 41881801],
}

FAKE_JOB = {
    "id": 41881551,
    "type": "job",
    "by": "ycombinator",
    "time": 1700000300,
    "title": "YC is hiring a software engineer",
    "url": "https://ycombinator.com/careers",
}

FAKE_COMMENT_1 = {
    "id": 41881600,
    "type": "comment",
    "by": "jsmith",
    "time": 1700000400,
    "text": "This is a really insightful article. I've been thinking about this for a while.",
    "parent": 41881548,
    "kids": [41881610, 41881611],
}

FAKE_COMMENT_2 = {
    "id": 41881601,
    "type": "comment",
    "by": "alice",
    "time": 1700000500,
    "text": "Disagree with the premise. The attention economy is more nuanced.",
    "parent": 41881548,
    "kids": [],
}

FAKE_COMMENT_3 = {
    "id": 41881602,
    "type": "comment",
    "by": "bob",
    "time": 1700000600,
    "text": "Related: there was a great talk at StrangeLoop about this topic.",
    "parent": 41881548,
}

FAKE_NESTED_COMMENT_1 = {
    "id": 41881610,
    "type": "comment",
    "by": "carol",
    "time": 1700000700,
    "text": "Agreed! The section on dopamine loops was especially good.",
    "parent": 41881600,
    "kids": [],
}

FAKE_NESTED_COMMENT_2 = {
    "id": 41881611,
    "type": "comment",
    "by": "dave",
    "time": 1700000800,
    "text": "I'd push back on that. The data doesn't support it.",
    "parent": 41881600,
}

FAKE_USER = {
    "id": "pg",
    "created": 1160418111,
    "karma": 157236,
    "about": "Bug fixer.",
    "submitted": [41881548, 41881549, 41881550, 21318552, 15975834],
}

FAKE_TOP_STORY_IDS = [41881548, 41881549, 41881550]
FAKE_NEW_STORY_IDS = [41881550, 41881549, 41881548]
FAKE_BEST_STORY_IDS = [41881548, 41881550, 41881549]
FAKE_ASK_STORY_IDS = [41881550]
FAKE_SHOW_STORY_IDS = [41881549]
FAKE_JOB_STORY_IDS = [41881551]
FAKE_MAX_ITEM = 41882000

# Map item IDs to their data
FAKE_ITEMS = {
    41881548: FAKE_STORY_1,
    41881549: FAKE_STORY_2,
    41881550: FAKE_STORY_3,
    41881551: FAKE_JOB,
    41881600: FAKE_COMMENT_1,
    41881601: FAKE_COMMENT_2,
    41881602: FAKE_COMMENT_3,
    41881610: FAKE_NESTED_COMMENT_1,
    41881611: FAKE_NESTED_COMMENT_2,
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/topstories.json": FAKE_TOP_STORY_IDS,
        "/newstories.json": FAKE_NEW_STORY_IDS,
        "/beststories.json": FAKE_BEST_STORY_IDS,
        "/askstories.json": FAKE_ASK_STORY_IDS,
        "/showstories.json": FAKE_SHOW_STORY_IDS,
        "/jobstories.json": FAKE_JOB_STORY_IDS,
        "/maxitem.json": FAKE_MAX_ITEM,
        "/user/pg.json": FAKE_USER,
    }
    # Add item endpoints
    for item_id, item_data in FAKE_ITEMS.items():
        defaults[f"/item/{item_id}.json"] = item_data

    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Match on path suffix.
        for path, data in defaults.items():
            if url.endswith(path):
                resp.json.return_value = data
                return resp
        resp.json.return_value = {}
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """HackerNewsService with mocked HTTP client."""
    from hackernews_mcp.service import HackerNewsService

    svc = HackerNewsService.__new__(HackerNewsService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked HackerNewsService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-hn", version="0.0.1")
    srv.register(service)
    return srv
