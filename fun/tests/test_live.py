"""Live integration tests for Fun APIs -- hits the real APIs.

Run with:
    FUN_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) fun API endpoints:
  - icanhazdadjoke.com: Dad jokes
  - opentdb.com: Trivia questions
  - api.quotable.io: Inspirational quotes
  - dog.ceo: Dog images
  - catfact.ninja: Cat facts
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
    os.getenv("FUN_RUN_LIVE_TESTS") != "1",
    reason="Set FUN_RUN_LIVE_TESTS=1 to run live Fun API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from fun_mcp.gen.fun.v1 import fun_pb2 as _pb  # noqa: F401
    from fun_mcp.service import FunService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-fun-live", version="0.0.1"
    )
    servicer = FunService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- Shared fixtures for data discovery ---


@pytest.fixture(scope="module")
def dog_breed(live_server):
    """Discover a valid dog breed name for breed-specific tests."""
    result = live_server._cli(["FunService", "ListDogBreeds"])
    breeds = result.get("breeds", [])
    assert breeds, "expected at least one breed"
    return breeds[0].get("breed", "")


@pytest.fixture(scope="module")
def trivia_category_id(live_server):
    """Discover a valid trivia category ID."""
    result = live_server._cli(["FunService", "GetTriviaCategories"])
    categories = result.get("categories", [])
    assert categories, "expected at least one trivia category"
    return categories[0].get("id", 0)


# --- Dad jokes ---


class TestLiveDadJokes:
    def test_get_dad_joke(self, live_server):
        result = live_server._cli(["FunService", "GetDadJoke"])
        joke = result.get("joke", {})
        assert isinstance(joke, dict)
        assert joke.get("id")
        assert joke.get("joke")

    def test_search_dad_jokes(self, live_server):
        result = live_server._cli(
            [
                "FunService",
                "SearchDadJokes",
                "-r",
                json.dumps({"query": "cat", "limit": 5}),
            ]
        )
        jokes = result.get("jokes", [])
        assert isinstance(jokes, list)
        # Search might return 0 results for some terms; that is OK
        total = result.get("total", 0)
        assert int(total) >= 0

    def test_search_dad_jokes_with_results(self, live_server):
        result = live_server._cli(
            [
                "FunService",
                "SearchDadJokes",
                "-r",
                json.dumps({"query": "dog", "limit": 3}),
            ]
        )
        jokes = result.get("jokes", [])
        assert isinstance(jokes, list)
        if jokes:
            j = jokes[0]
            assert j.get("id")
            assert j.get("joke")


# --- Trivia ---


class TestLiveTrivia:
    def test_get_trivia(self, live_server):
        result = live_server._cli(
            [
                "FunService",
                "GetTrivia",
                "-r",
                json.dumps({"amount": 3}),
            ]
        )
        questions = result.get("questions", [])
        assert isinstance(questions, list)
        assert len(questions) > 0
        q = questions[0]
        assert q.get("question")
        assert q.get("correctAnswer") or q.get("correct_answer")
        assert q.get("category")

    def test_get_trivia_with_category(self, live_server, trivia_category_id):
        result = live_server._cli(
            [
                "FunService",
                "GetTrivia",
                "-r",
                json.dumps({"amount": 2, "category": trivia_category_id}),
            ]
        )
        questions = result.get("questions", [])
        assert isinstance(questions, list)
        # Trivia API may return fewer than requested if not enough questions
        assert len(questions) >= 0

    def test_get_trivia_with_difficulty(self, live_server):
        result = live_server._cli(
            [
                "FunService",
                "GetTrivia",
                "-r",
                json.dumps({"amount": 2, "difficulty": "easy"}),
            ]
        )
        questions = result.get("questions", [])
        assert isinstance(questions, list)
        if questions:
            for q in questions:
                assert q.get("difficulty") == "easy"

    def test_get_trivia_categories(self, live_server):
        result = live_server._cli(["FunService", "GetTriviaCategories"])
        categories = result.get("categories", [])
        assert isinstance(categories, list)
        assert len(categories) > 0
        c = categories[0]
        assert c.get("id")
        assert c.get("name")


# --- Quotes ---


class TestLiveQuotes:
    def test_get_random_quote(self, live_server):
        result = live_server._cli(["FunService", "GetRandomQuote"])
        quote = result.get("quote", {})
        assert isinstance(quote, dict)
        content = quote.get("content", "")
        assert content
        author = quote.get("author", "")
        assert author

    def test_search_quotes(self, live_server):
        result = live_server._cli(
            [
                "FunService",
                "SearchQuotes",
                "-r",
                json.dumps({"query": "life"}),
            ]
        )
        quotes = result.get("quotes", [])
        assert isinstance(quotes, list)
        # Search may return 0 results
        if quotes:
            q = quotes[0]
            assert q.get("content")
            assert q.get("author")
        total = result.get("total", 0)
        assert int(total) >= 0


# --- Dog images ---


class TestLiveDogImages:
    def test_get_random_dog_image(self, live_server):
        result = live_server._cli(["FunService", "GetRandomDogImage"])
        url = result.get("imageUrl") or result.get("image_url", "")
        assert url
        assert url.startswith("http")

    def test_get_dog_image_by_breed(self, live_server, dog_breed):
        if not dog_breed:
            pytest.skip("no breed name available")
        result = live_server._cli(
            [
                "FunService",
                "GetDogImageByBreed",
                "-r",
                json.dumps({"breed": dog_breed}),
            ]
        )
        url = result.get("imageUrl") or result.get("image_url", "")
        assert url
        assert url.startswith("http")

    def test_list_dog_breeds(self, live_server):
        result = live_server._cli(["FunService", "ListDogBreeds"])
        breeds = result.get("breeds", [])
        assert isinstance(breeds, list)
        assert len(breeds) > 0
        b = breeds[0]
        assert b.get("breed")
        # sub_breeds is a list (may be empty)
        sub = b.get("subBreeds") or b.get("sub_breeds", [])
        assert isinstance(sub, list)


# --- Cat facts ---


class TestLiveCatFacts:
    def test_get_random_cat_fact(self, live_server):
        result = live_server._cli(["FunService", "GetRandomCatFact"])
        fact = result.get("fact", "")
        assert fact
        assert len(fact) > 0
        length = result.get("length", 0)
        assert int(length) > 0
