"""Shared fixtures for Open Library MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openlibrary_mcp.gen.openlibrary.v1 import openlibrary_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real Open Library API return shapes
# ---------------------------------------------------------------------------

FAKE_SEARCH = {
    "numFound": 2,
    "docs": [
        {
            "title": "The Lord of the Rings",
            "author_name": ["J.R.R. Tolkien"],
            "first_publish_year": 1954,
            "isbn": ["9780261103573"],
            "cover_i": 8474036,
            "number_of_pages_median": 1216,
            "subject": ["Fantasy", "Fiction", "Adventure", "Epic fantasy"],
            "key": "/works/OL45883W",
        },
        {
            "title": "The Hobbit",
            "author_name": ["J.R.R. Tolkien"],
            "first_publish_year": 1937,
            "isbn": ["9780547928227"],
            "cover_i": 8406786,
            "number_of_pages_median": 310,
            "subject": ["Fantasy", "Fiction", "Children's literature"],
            "key": "/works/OL262758W",
        },
    ],
}

FAKE_SEARCH_BY_AUTHOR = {
    "numFound": 1,
    "docs": [
        {
            "title": "1984",
            "author_name": ["George Orwell"],
            "first_publish_year": 1949,
            "isbn": ["9780451524935"],
            "cover_i": 8575964,
            "number_of_pages_median": 328,
            "subject": ["Dystopia", "Political fiction"],
            "key": "/works/OL1168083W",
        },
    ],
}

FAKE_SUBJECT = {
    "name": "Fantasy",
    "work_count": 50000,
    "works": [
        {
            "title": "A Game of Thrones",
            "authors": [{"name": "George R.R. Martin"}],
            "key": "/works/OL17346379W",
            "cover_id": 8451036,
            "edition_count": 85,
            "first_publish_year": 1996,
        },
        {
            "title": "The Name of the Wind",
            "authors": [{"name": "Patrick Rothfuss"}],
            "key": "/works/OL5735363W",
            "cover_id": 6840270,
            "edition_count": 42,
            "first_publish_year": 2007,
        },
    ],
}

FAKE_BOOK = {
    "title": "The Lord of the Rings",
    "description": {"value": "An epic high-fantasy novel by English author J.R.R. Tolkien."},
    "subjects": ["Fantasy", "Fiction", "Adventure"],
    "covers": [8474036, 12345],
    "created": {"value": "2008-04-01T03:28:50.625462"},
    "key": "/works/OL45883W",
}

FAKE_EDITION = {
    "title": "The Lord of the Rings",
    "publishers": ["Houghton Mifflin"],
    "publish_date": "2004",
    "isbn_13": ["9780618640157"],
    "isbn_10": ["0618640150"],
    "number_of_pages": 1216,
    "covers": [8474036],
    "key": "/books/OL7353617M",
}

FAKE_AUTHOR = {
    "name": "J.R.R. Tolkien",
    "bio": {"value": "John Ronald Reuel Tolkien was an English writer, poet, and philologist."},
    "birth_date": "3 January 1892",
    "death_date": "2 September 1973",
    "photos": [6304727, 6271462],
    "links": [
        {"title": "Wikipedia", "url": "https://en.wikipedia.org/wiki/J._R._R._Tolkien"},
    ],
    "key": "/authors/OL23919A",
}

FAKE_AUTHOR_WORKS = {
    "size": 50,
    "entries": [
        {
            "title": "The Lord of the Rings",
            "key": "/works/OL45883W",
            "covers": [8474036],
            "first_publish_year": 1954,
        },
        {
            "title": "The Hobbit",
            "key": "/works/OL262758W",
            "covers": [8406786],
            "first_publish_year": 1937,
        },
    ],
}

FAKE_ISBN = {
    "title": "The Lord of the Rings",
    "publishers": ["Houghton Mifflin"],
    "publish_date": "2004",
    "isbn_13": ["9780618640157"],
    "isbn_10": ["0618640150"],
    "number_of_pages": 1216,
    "covers": [8474036],
    "key": "/books/OL7353617M",
}

FAKE_RECENT_CHANGES = [
    {
        "kind": "edit-book",
        "author": {"key": "/people/ImportBot"},
        "timestamp": "2025-01-15T10:00:00Z",
        "comment": "Updated book metadata",
        "id": "12345",
    },
    {
        "kind": "add-book",
        "author": {"key": "/people/TestUser"},
        "timestamp": "2025-01-15T09:00:00Z",
        "comment": "Added new book",
        "id": "12346",
    },
]

FAKE_TRENDING = {
    "works": [
        {
            "title": "Dune",
            "author_name": ["Frank Herbert"],
            "key": "/works/OL893415W",
            "cover_i": 8231856,
            "first_publish_year": 1965,
            "availability": {"status": "borrow_available"},
        },
        {
            "title": "Project Hail Mary",
            "author_name": ["Andy Weir"],
            "key": "/works/OL24177628W",
            "cover_i": 12578907,
            "first_publish_year": 2021,
            "availability": {"status": "borrow_available"},
        },
    ],
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/search.json": FAKE_SEARCH,
        "/subjects/fantasy.json": FAKE_SUBJECT,
        "/works/OL45883W.json": FAKE_BOOK,
        "/books/OL7353617M.json": FAKE_EDITION,
        "/authors/OL23919A.json": FAKE_AUTHOR,
        "/authors/OL23919A/works.json": FAKE_AUTHOR_WORKS,
        "/isbn/9780261103573.json": FAKE_ISBN,
        "/recentchanges.json": FAKE_RECENT_CHANGES,
        "/trending/daily.json": FAKE_TRENDING,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()

        # Check for author search vs book search.
        if "/search.json" in url and params and "author" in params:
            resp.json.return_value = FAKE_SEARCH_BY_AUTHOR
            return resp

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
    """OpenLibraryService with mocked HTTP client."""
    from openlibrary_mcp.service import OpenLibraryService

    svc = OpenLibraryService.__new__(OpenLibraryService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked OpenLibraryService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-ol", version="0.0.1")
    srv.register(service)
    return srv
