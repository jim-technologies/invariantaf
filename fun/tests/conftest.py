"""Shared fixtures for Fun MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fun_mcp.gen.fun.v1 import fun_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real API return shapes
# ---------------------------------------------------------------------------

FAKE_DAD_JOKE = {
    "id": "R7UfaahVfFd",
    "joke": "My dog used to chase people on a bike a lot. It got so bad I had to take his bike away.",
    "status": 200,
}

FAKE_DAD_JOKE_SEARCH = {
    "current_page": 1,
    "limit": 20,
    "next_page": 1,
    "previous_page": 1,
    "results": [
        {"id": "abc123", "joke": "What do you call a fake noodle? An impasta."},
        {"id": "def456", "joke": "I used to hate facial hair, but then it grew on me."},
    ],
    "search_term": "noodle",
    "status": 200,
    "total_jokes": 2,
    "total_pages": 1,
}

FAKE_TRIVIA = {
    "response_code": 0,
    "results": [
        {
            "type": "multiple",
            "difficulty": "medium",
            "category": "Science &amp; Nature",
            "question": "What is the chemical symbol for gold?",
            "correct_answer": "Au",
            "incorrect_answers": ["Ag", "Fe", "Gd"],
        },
        {
            "type": "boolean",
            "difficulty": "easy",
            "category": "General Knowledge",
            "question": "The Great Wall of China is visible from space.",
            "correct_answer": "False",
            "incorrect_answers": ["True"],
        },
    ],
}

FAKE_TRIVIA_CATEGORIES = {
    "trivia_categories": [
        {"id": 9, "name": "General Knowledge"},
        {"id": 18, "name": "Science: Computers"},
        {"id": 21, "name": "Sports"},
        {"id": 22, "name": "Geography"},
        {"id": 23, "name": "History"},
    ],
}

FAKE_RANDOM_QUOTE = [
    {
        "_id": "q1abc",
        "content": "The only way to do great work is to love what you do.",
        "author": "Steve Jobs",
        "tags": ["inspirational", "work"],
        "length": 52,
    }
]

FAKE_SEARCH_QUOTES = {
    "count": 2,
    "totalCount": 2,
    "page": 1,
    "totalPages": 1,
    "results": [
        {
            "_id": "q2def",
            "content": "In the middle of difficulty lies opportunity.",
            "author": "Albert Einstein",
            "tags": ["wisdom"],
            "length": 45,
        },
        {
            "_id": "q3ghi",
            "content": "Life is what happens when you're busy making other plans.",
            "author": "John Lennon",
            "tags": ["life"],
            "length": 56,
        },
    ],
}

FAKE_RANDOM_DOG = {
    "message": "https://images.dog.ceo/breeds/labrador/n02099712_1234.jpg",
    "status": "success",
}

FAKE_DOG_BY_BREED = {
    "message": "https://images.dog.ceo/breeds/husky/n02110185_5678.jpg",
    "status": "success",
}

FAKE_DOG_BREEDS = {
    "message": {
        "labrador": [],
        "poodle": ["standard", "miniature", "toy"],
        "husky": [],
        "corgi": ["cardigan"],
    },
    "status": "success",
}

FAKE_CAT_FACT = {
    "fact": "Cats have over 20 vocalizations, including the purr, meow, and hiss.",
    "length": 70,
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "https://icanhazdadjoke.com": FAKE_DAD_JOKE,
        "https://icanhazdadjoke.com/search": FAKE_DAD_JOKE_SEARCH,
        "https://opentdb.com/api.php": FAKE_TRIVIA,
        "https://opentdb.com/api_category.php": FAKE_TRIVIA_CATEGORIES,
        "https://api.quotable.io/quotes/random": FAKE_RANDOM_QUOTE,
        "https://api.quotable.io/search/quotes": FAKE_SEARCH_QUOTES,
        "https://dog.ceo/api/breeds/image/random": FAKE_RANDOM_DOG,
        "https://dog.ceo/api/breed/husky/images/random": FAKE_DOG_BY_BREED,
        "https://dog.ceo/api/breeds/list/all": FAKE_DOG_BREEDS,
        "https://catfact.ninja/fact": FAKE_CAT_FACT,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None, headers=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Match on exact URL
        for path, data in defaults.items():
            if url == path:
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
    """FunService with mocked HTTP client."""
    from fun_mcp.service import FunService

    svc = FunService.__new__(FunService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked FunService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-fun", version="0.0.1")
    srv.register(service)
    return srv
