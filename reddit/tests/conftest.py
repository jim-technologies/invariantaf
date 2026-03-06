"""Shared fixtures for Reddit MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reddit_mcp.gen.reddit.v1 import reddit_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real Reddit JSON API return shapes
# ---------------------------------------------------------------------------

FAKE_LISTING_POSTS = {
    "data": {
        "children": [
            {
                "kind": "t3",
                "data": {
                    "id": "abc123",
                    "title": "Test Post Title",
                    "selftext": "This is the body of the test post.",
                    "author": "testuser",
                    "subreddit": "python",
                    "score": 1500,
                    "num_comments": 200,
                    "url": "https://www.reddit.com/r/python/comments/abc123/test_post_title/",
                    "permalink": "/r/python/comments/abc123/test_post_title/",
                    "created_utc": 1700000000.0,
                    "is_self": True,
                    "thumbnail": "self",
                },
            },
            {
                "kind": "t3",
                "data": {
                    "id": "def456",
                    "title": "Another Post",
                    "selftext": "",
                    "author": "otheruser",
                    "subreddit": "python",
                    "score": 500,
                    "num_comments": 50,
                    "url": "https://example.com/article",
                    "permalink": "/r/python/comments/def456/another_post/",
                    "created_utc": 1700003600.0,
                    "is_self": False,
                    "thumbnail": "https://thumb.example.com/img.jpg",
                },
            },
        ],
    },
}

FAKE_POST_DETAIL = [
    # First listing: the post itself
    {
        "data": {
            "children": [
                {
                    "kind": "t3",
                    "data": {
                        "id": "abc123",
                        "title": "Test Post Title",
                        "selftext": "This is the body of the test post.",
                        "author": "testuser",
                        "subreddit": "python",
                        "score": 1500,
                        "num_comments": 200,
                        "url": "https://www.reddit.com/r/python/comments/abc123/test_post_title/",
                        "permalink": "/r/python/comments/abc123/test_post_title/",
                        "created_utc": 1700000000.0,
                        "is_self": True,
                        "thumbnail": "self",
                    },
                },
            ],
        },
    },
    # Second listing: comments
    {
        "data": {
            "children": [
                {
                    "kind": "t1",
                    "data": {
                        "id": "cmt001",
                        "author": "commenter1",
                        "body": "Great post!",
                        "score": 100,
                        "created_utc": 1700001000.0,
                        "permalink": "/r/python/comments/abc123/test_post_title/cmt001/",
                        "replies": {
                            "data": {
                                "children": [
                                    {
                                        "kind": "t1",
                                        "data": {
                                            "id": "cmt002",
                                            "author": "replier1",
                                            "body": "Thanks!",
                                            "score": 20,
                                            "created_utc": 1700002000.0,
                                            "permalink": "/r/python/comments/abc123/test_post_title/cmt002/",
                                            "replies": "",
                                        },
                                    },
                                ],
                            },
                        },
                    },
                },
                {
                    "kind": "t1",
                    "data": {
                        "id": "cmt003",
                        "author": "commenter2",
                        "body": "Interesting discussion.",
                        "score": 50,
                        "created_utc": 1700003000.0,
                        "permalink": "/r/python/comments/abc123/test_post_title/cmt003/",
                        "replies": "",
                    },
                },
            ],
        },
    },
]

FAKE_SEARCH_RESULTS = {
    "data": {
        "children": [
            {
                "kind": "t3",
                "data": {
                    "id": "srch01",
                    "title": "Python tutorial for beginners",
                    "selftext": "A comprehensive tutorial.",
                    "author": "educator",
                    "subreddit": "learnpython",
                    "score": 3000,
                    "num_comments": 150,
                    "url": "https://www.reddit.com/r/learnpython/comments/srch01/python_tutorial/",
                    "permalink": "/r/learnpython/comments/srch01/python_tutorial/",
                    "created_utc": 1700010000.0,
                    "is_self": True,
                    "thumbnail": "self",
                },
            },
        ],
    },
}

FAKE_SUBREDDIT_ABOUT = {
    "data": {
        "name": "t5_2qh0y",
        "display_name": "python",
        "title": "Python",
        "public_description": "News about the dynamic, interpreted, interactive, object-oriented, extensible programming language Python.",
        "subscribers": 1500000,
        "accounts_active": 5000,
        "created_utc": 1230000000.0,
        "url": "/r/python/",
        "over18": False,
    },
}

FAKE_USER_ABOUT = {
    "data": {
        "name": "testuser",
        "link_karma": 10000,
        "comment_karma": 50000,
        "created_utc": 1400000000.0,
        "subreddit": {
            "public_description": "I like Python and open source.",
        },
        "is_gold": True,
        "verified": True,
    },
}

FAKE_USER_POSTS = {
    "data": {
        "children": [
            {
                "kind": "t3",
                "data": {
                    "id": "usr01",
                    "title": "My project update",
                    "selftext": "Here is my latest project.",
                    "author": "testuser",
                    "subreddit": "python",
                    "score": 800,
                    "num_comments": 60,
                    "url": "https://www.reddit.com/r/python/comments/usr01/my_project_update/",
                    "permalink": "/r/python/comments/usr01/my_project_update/",
                    "created_utc": 1700050000.0,
                    "is_self": True,
                    "thumbnail": "self",
                },
            },
        ],
    },
}

FAKE_POPULAR_SUBREDDITS = {
    "data": {
        "children": [
            {
                "kind": "t5",
                "data": {
                    "name": "t5_2cneq",
                    "display_name": "AskReddit",
                    "title": "Ask Reddit...",
                    "public_description": "Ask and answer thought-provoking questions.",
                    "subscribers": 45000000,
                    "accounts_active": 50000,
                    "created_utc": 1201000000.0,
                    "url": "/r/AskReddit/",
                    "over18": False,
                },
            },
            {
                "kind": "t5",
                "data": {
                    "name": "t5_2qh33",
                    "display_name": "funny",
                    "title": "funny",
                    "public_description": "Reddit's largest humour depository.",
                    "subscribers": 40000000,
                    "accounts_active": 30000,
                    "created_utc": 1201100000.0,
                    "url": "/r/funny/",
                    "over18": False,
                },
            },
        ],
    },
}

FAKE_FRONT_PAGE = {
    "data": {
        "children": [
            {
                "kind": "t3",
                "data": {
                    "id": "fp001",
                    "title": "Front page post",
                    "selftext": "This is on the front page.",
                    "author": "frontpageuser",
                    "subreddit": "worldnews",
                    "score": 50000,
                    "num_comments": 3000,
                    "url": "https://www.reddit.com/r/worldnews/comments/fp001/front_page_post/",
                    "permalink": "/r/worldnews/comments/fp001/front_page_post/",
                    "created_utc": 1700060000.0,
                    "is_self": True,
                    "thumbnail": "self",
                },
            },
        ],
    },
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/r/python/hot.json": FAKE_LISTING_POSTS,
        "/r/python/top.json": FAKE_LISTING_POSTS,
        "/r/python/new.json": FAKE_LISTING_POSTS,
        "/r/python/comments/abc123.json": FAKE_POST_DETAIL,
        "/search.json": FAKE_SEARCH_RESULTS,
        "/r/python/about.json": FAKE_SUBREDDIT_ABOUT,
        "/user/testuser/about.json": FAKE_USER_ABOUT,
        "/user/testuser/submitted.json": FAKE_USER_POSTS,
        "/subreddits/popular.json": FAKE_POPULAR_SUBREDDITS,
        "/.json": FAKE_FRONT_PAGE,
    }
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
    """RedditService with mocked HTTP client."""
    from reddit_mcp.service import RedditService

    svc = RedditService.__new__(RedditService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked RedditService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-reddit", version="0.0.1")
    srv.register(service)
    return srv
