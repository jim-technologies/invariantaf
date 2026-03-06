"""Shared fixtures for Wikipedia MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wikipedia_mcp.gen.wikipedia.v1 import wikipedia_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real Wikipedia API return shapes
# ---------------------------------------------------------------------------

FAKE_SEARCH = {
    "query": {
        "searchinfo": {"totalhits": 12345},
        "search": [
            {
                "pageid": 100,
                "title": "Quantum computing",
                "snippet": "<span class=\"searchmatch\">Quantum</span> computing is...",
                "wordcount": 8500,
                "timestamp": "2025-01-10T12:00:00Z",
            },
            {
                "pageid": 200,
                "title": "Quantum mechanics",
                "snippet": "<span class=\"searchmatch\">Quantum</span> mechanics is...",
                "wordcount": 15000,
                "timestamp": "2025-01-09T08:00:00Z",
            },
        ],
    }
}

FAKE_PAGE_SUMMARY = {
    "title": "Albert Einstein",
    "extract": "Albert Einstein was a German-born theoretical physicist.",
    "thumbnail": {"source": "https://upload.wikimedia.org/thumb/einstein.jpg"},
    "description": "German-born theoretical physicist (1879-1955)",
    "pageid": 736,
    "content_urls": {
        "desktop": {"page": "https://en.wikipedia.org/wiki/Albert_Einstein"},
    },
}

FAKE_FULL_PAGE = {
    "query": {
        "pages": {
            "736": {
                "pageid": 736,
                "title": "Albert Einstein",
                "extract": "Albert Einstein (14 March 1879 - 18 April 1955) was a German-born theoretical physicist. He developed the theory of relativity, one of the two pillars of modern physics.",
            }
        }
    }
}

FAKE_RANDOM_SUMMARY = {
    "title": "Platypus",
    "extract": "The platypus is a semiaquatic, egg-laying mammal endemic to eastern Australia.",
    "thumbnail": {"source": "https://upload.wikimedia.org/thumb/platypus.jpg"},
    "description": "Species of egg-laying mammal",
    "pageid": 24407,
    "content_urls": {
        "desktop": {"page": "https://en.wikipedia.org/wiki/Platypus"},
    },
}

FAKE_ON_THIS_DAY = {
    "events": [
        {
            "year": 1776,
            "text": "The United States Declaration of Independence is adopted.",
            "pages": [
                {
                    "title": "United States Declaration of Independence",
                    "extract": "The Declaration of Independence is the founding document...",
                    "thumbnail": {"source": "https://upload.wikimedia.org/thumb/declaration.jpg"},
                    "description": "Founding document of the United States",
                    "pageid": 3355,
                    "content_urls": {
                        "desktop": {"page": "https://en.wikipedia.org/wiki/United_States_Declaration_of_Independence"},
                    },
                },
            ],
        },
        {
            "year": 2012,
            "text": "The Higgs boson discovery is announced at CERN.",
            "pages": [
                {
                    "title": "Higgs boson",
                    "extract": "The Higgs boson is an elementary particle...",
                    "thumbnail": None,
                    "description": "Elementary particle",
                    "pageid": 40427,
                    "content_urls": {
                        "desktop": {"page": "https://en.wikipedia.org/wiki/Higgs_boson"},
                    },
                },
            ],
        },
    ]
}

FAKE_FEATURED = {
    "mostread": {
        "date": "2025-01-14",
        "articles": [
            {
                "title": "ChatGPT",
                "views": 250000,
                "extract": "ChatGPT is an artificial intelligence chatbot.",
                "thumbnail": {"source": "https://upload.wikimedia.org/thumb/chatgpt.png"},
                "description": "AI chatbot by OpenAI",
            },
            {
                "title": "Super Bowl LIX",
                "views": 180000,
                "extract": "Super Bowl LIX is an upcoming American football game.",
                "thumbnail": {"source": "https://upload.wikimedia.org/thumb/superbowl.jpg"},
                "description": "59th Super Bowl",
            },
        ],
    }
}

FAKE_LANGLINKS = {
    "query": {
        "pages": {
            "736": {
                "pageid": 736,
                "title": "Albert Einstein",
                "langlinks": [
                    {"lang": "fr", "*": "Albert Einstein"},
                    {"lang": "de", "*": "Albert Einstein"},
                    {"lang": "ja", "*": "\u30a2\u30eb\u30d9\u30eb\u30c8\u30fb\u30a2\u30a4\u30f3\u30b7\u30e5\u30bf\u30a4\u30f3"},
                ],
            }
        }
    }
}

FAKE_CATEGORIES = {
    "query": {
        "pages": {
            "736": {
                "pageid": 736,
                "title": "Albert Einstein",
                "categories": [
                    {"title": "Category:Nobel laureates in Physics"},
                    {"title": "Category:German physicists"},
                    {"title": "Category:20th-century physicists"},
                ],
            }
        }
    }
}

FAKE_LINKS = {
    "query": {
        "pages": {
            "736": {
                "pageid": 736,
                "title": "Albert Einstein",
                "links": [
                    {"title": "Theory of relativity"},
                    {"title": "Photoelectric effect"},
                    {"title": "Nobel Prize in Physics"},
                ],
            }
        }
    }
}

FAKE_IMAGES = {
    "query": {
        "pages": {
            "736": {
                "pageid": 736,
                "title": "Albert Einstein",
                "images": [
                    {"title": "File:Albert Einstein Head.jpg"},
                    {"title": "File:Einstein 1921 by F Schmutzer.jpg"},
                    {"title": "File:Nobel Prize.png"},
                ],
            }
        }
    }
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        # Action API endpoints (matched by action= param)
        ("action_query", "list_search"): FAKE_SEARCH,
        ("action_query", "prop_extracts"): FAKE_FULL_PAGE,
        ("action_query", "prop_langlinks"): FAKE_LANGLINKS,
        ("action_query", "prop_categories"): FAKE_CATEGORIES,
        ("action_query", "prop_links"): FAKE_LINKS,
        ("action_query", "prop_images"): FAKE_IMAGES,
        # REST API endpoints (matched by URL path)
        "/page/summary/": FAKE_PAGE_SUMMARY,
        "/page/random/summary": FAKE_RANDOM_SUMMARY,
        "/feed/onthisday/": FAKE_ON_THIS_DAY,
        "/feed/featured/": FAKE_FEATURED,
    }

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()

        # Action API: match by params
        if params and params.get("action") == "query":
            if params.get("list") == "search":
                resp.json.return_value = defaults[("action_query", "list_search")]
                return resp
            prop = params.get("prop", "")
            if prop == "extracts":
                resp.json.return_value = defaults[("action_query", "prop_extracts")]
                return resp
            if prop == "langlinks":
                resp.json.return_value = defaults[("action_query", "prop_langlinks")]
                return resp
            if prop == "categories":
                resp.json.return_value = defaults[("action_query", "prop_categories")]
                return resp
            if prop == "links":
                resp.json.return_value = defaults[("action_query", "prop_links")]
                return resp
            if prop == "images":
                resp.json.return_value = defaults[("action_query", "prop_images")]
                return resp

        # REST API: match by URL path
        for path_prefix, data in defaults.items():
            if isinstance(path_prefix, str) and path_prefix in url:
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
    """WikipediaService with mocked HTTP client."""
    from wikipedia_mcp.service import WikipediaService

    svc = WikipediaService.__new__(WikipediaService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked WikipediaService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-wiki", version="0.0.1")
    srv.register(service)
    return srv
