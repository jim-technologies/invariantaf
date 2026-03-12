"""Live integration tests for Open Library API -- hits the real API.

Run with:
    OPENLIBRARY_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) Open Library API endpoints.
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
    os.getenv("OPENLIBRARY_RUN_LIVE_TESTS") != "1",
    reason="Set OPENLIBRARY_RUN_LIVE_TESTS=1 to run live Open Library API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from openlibrary_mcp.gen.openlibrary.v1 import openlibrary_pb2 as _openlibrary_pb2  # noqa: F401
    from openlibrary_mcp.service import OpenLibraryService
    from invariant import Server

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-openlibrary-live", version="0.0.1"
    )
    svc = OpenLibraryService()
    srv.register(svc)
    yield srv
    srv.stop()


# --- Shared fixtures for data discovery ---


@pytest.fixture(scope="module")
def discovered_book(live_server):
    """Discover a book via search for tests that need a work key."""
    result = live_server._cli(
        ["OpenLibraryService", "SearchBooks", "-r", json.dumps({"query": "lord of the rings", "limit": 1})]
    )
    books = result.get("books", [])
    assert books, "expected at least one book from search"
    return books[0]


@pytest.fixture(scope="module")
def discovered_author_id(live_server):
    """Return a known author ID for lookup tests."""
    # J.R.R. Tolkien is a stable, well-known author
    return "OL23919A"


# --- Book search ---


class TestLiveSearchBooks:
    def test_search_books(self, live_server):
        result = live_server._cli(
            ["OpenLibraryService", "SearchBooks", "-r", json.dumps({"query": "dune", "limit": 3})]
        )
        assert "books" in result
        books = result["books"]
        assert isinstance(books, list)
        assert len(books) > 0
        b = books[0]
        assert "title" in b
        assert "key" in b

    def test_search_by_author(self, live_server):
        result = live_server._cli(
            ["OpenLibraryService", "SearchByAuthor", "-r", json.dumps({"name": "tolkien", "limit": 3})]
        )
        assert "books" in result
        books = result["books"]
        assert isinstance(books, list)
        assert len(books) > 0

    def test_search_by_subject(self, live_server):
        result = live_server._cli(
            ["OpenLibraryService", "SearchBySubject", "-r", json.dumps({"subject": "fantasy", "limit": 3})]
        )
        assert "works" in result
        works = result["works"]
        assert isinstance(works, list)
        assert len(works) > 0
        w = works[0]
        assert "title" in w


# --- Book / Edition / Author lookup ---


class TestLiveBookLookup:
    def test_get_book(self, live_server):
        result = live_server._cli(
            ["OpenLibraryService", "GetBook", "-r", json.dumps({"work_id": "OL45883W"})]
        )
        assert result.get("title"), "expected a title for The Lord of the Rings"
        assert "key" in result

    def test_get_edition(self, live_server):
        result = live_server._cli(
            ["OpenLibraryService", "GetEdition", "-r", json.dumps({"edition_id": "OL7353617M"})]
        )
        assert result.get("title"), "expected a title for the edition"
        assert "key" in result

    def test_get_book_by_isbn(self, live_server):
        result = live_server._cli(
            ["OpenLibraryService", "GetBookByISBN", "-r", json.dumps({"isbn": "9780261103573"})]
        )
        assert result.get("title"), "expected a title for the ISBN lookup"


# --- Author ---


class TestLiveAuthor:
    def test_get_author(self, live_server, discovered_author_id):
        result = live_server._cli(
            ["OpenLibraryService", "GetAuthor", "-r", json.dumps({"author_id": discovered_author_id})]
        )
        assert result.get("name"), "expected author name"
        assert "key" in result

    def test_get_author_works(self, live_server, discovered_author_id):
        result = live_server._cli(
            [
                "OpenLibraryService",
                "GetAuthorWorks",
                "-r",
                json.dumps({"author_id": discovered_author_id, "limit": 3}),
            ]
        )
        assert "works" in result
        works = result["works"]
        assert isinstance(works, list)
        assert len(works) > 0


# --- Trending / Recent ---


class TestLiveTrending:
    def test_get_trending_books(self, live_server):
        result = live_server._cli(
            ["OpenLibraryService", "GetTrendingBooks", "-r", json.dumps({"limit": 3})]
        )
        assert "books" in result
        books = result["books"]
        assert isinstance(books, list)
        # Trending may sometimes be empty, so just check structure
        if books:
            assert "title" in books[0]

    def test_get_recent_changes(self, live_server):
        result = live_server._cli(
            ["OpenLibraryService", "GetRecentChanges", "-r", json.dumps({"limit": 3})]
        )
        assert "changes" in result
        changes = result["changes"]
        assert isinstance(changes, list)
        assert len(changes) > 0
        c = changes[0]
        assert "kind" in c
        assert "timestamp" in c
