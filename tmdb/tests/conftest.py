"""Shared fixtures for TMDB MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tmdb_mcp.gen.tmdb.v1 import tmdb_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real TMDB API return shapes
# ---------------------------------------------------------------------------

FAKE_SEARCH_MOVIES = {
    "page": 1,
    "total_results": 2,
    "total_pages": 1,
    "results": [
        {
            "id": 550,
            "title": "Fight Club",
            "overview": "An insomniac office worker and a devil-may-care soap maker form an underground fight club.",
            "release_date": "1999-10-15",
            "vote_average": 8.4,
            "vote_count": 25000,
            "popularity": 50.5,
            "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
            "backdrop_path": "/hZkgoQYus5dXo3H8T7Uef6DNknx.jpg",
            "genre_ids": [18, 53],
            "original_language": "en",
            "adult": False,
        },
        {
            "id": 680,
            "title": "Pulp Fiction",
            "overview": "The lives of two mob hitmen intertwine in four tales of violence and redemption.",
            "release_date": "1994-09-10",
            "vote_average": 8.5,
            "vote_count": 24000,
            "popularity": 45.2,
            "poster_path": "/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg",
            "backdrop_path": "/suaEOtk1N1sgg2MTM7oZd2cfVp3.jpg",
            "genre_ids": [53, 80],
            "original_language": "en",
            "adult": False,
        },
    ],
}

FAKE_SEARCH_TV = {
    "page": 1,
    "total_results": 1,
    "total_pages": 1,
    "results": [
        {
            "id": 1396,
            "name": "Breaking Bad",
            "overview": "A high school chemistry teacher diagnosed with terminal lung cancer turns to manufacturing methamphetamine.",
            "first_air_date": "2008-01-20",
            "vote_average": 8.9,
            "vote_count": 12000,
            "popularity": 80.3,
            "poster_path": "/ggFHVNu6YYI5L9pCfOacjizRGt.jpg",
            "backdrop_path": "/tsRy63Mu5cu8etL1X7ZLyf7UP1M.jpg",
            "genre_ids": [18, 80],
            "original_language": "en",
        },
    ],
}

FAKE_MOVIE_DETAIL = {
    "id": 550,
    "title": "Fight Club",
    "overview": "An insomniac office worker and a devil-may-care soap maker form an underground fight club.",
    "release_date": "1999-10-15",
    "vote_average": 8.4,
    "vote_count": 25000,
    "genres": [
        {"id": 18, "name": "Drama"},
        {"id": 53, "name": "Thriller"},
    ],
    "runtime": 139,
    "budget": 63000000,
    "revenue": 100853753,
    "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
    "backdrop_path": "/hZkgoQYus5dXo3H8T7Uef6DNknx.jpg",
    "tagline": "Mischief. Mayhem. Soap.",
    "status": "Released",
    "original_language": "en",
    "popularity": 50.5,
    "homepage": "http://www.foxmovies.com/movies/fight-club",
    "imdb_id": "tt0137523",
}

FAKE_TV_DETAIL = {
    "id": 1396,
    "name": "Breaking Bad",
    "overview": "A high school chemistry teacher diagnosed with terminal lung cancer turns to manufacturing methamphetamine.",
    "first_air_date": "2008-01-20",
    "vote_average": 8.9,
    "vote_count": 12000,
    "genres": [
        {"id": 18, "name": "Drama"},
        {"id": 80, "name": "Crime"},
    ],
    "number_of_seasons": 5,
    "number_of_episodes": 62,
    "status": "Ended",
    "poster_path": "/ggFHVNu6YYI5L9pCfOacjizRGt.jpg",
    "backdrop_path": "/tsRy63Mu5cu8etL1X7ZLyf7UP1M.jpg",
    "tagline": "Remember my name.",
    "original_language": "en",
    "popularity": 80.3,
    "homepage": "http://www.amc.com/shows/breaking-bad",
    "type": "Scripted",
}

FAKE_TRENDING = {
    "page": 1,
    "total_results": 2,
    "total_pages": 1,
    "results": [
        {
            "id": 550,
            "title": "Fight Club",
            "name": "",
            "media_type": "movie",
            "overview": "An insomniac office worker...",
            "release_date": "1999-10-15",
            "first_air_date": "",
            "vote_average": 8.4,
            "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
            "popularity": 50.5,
        },
        {
            "id": 1396,
            "title": "",
            "name": "Breaking Bad",
            "media_type": "tv",
            "overview": "A high school chemistry teacher...",
            "release_date": "",
            "first_air_date": "2008-01-20",
            "vote_average": 8.9,
            "poster_path": "/ggFHVNu6YYI5L9pCfOacjizRGt.jpg",
            "popularity": 80.3,
        },
    ],
}

FAKE_MOVIE_CREDITS = {
    "id": 550,
    "cast": [
        {
            "id": 819,
            "name": "Edward Norton",
            "character": "The Narrator",
            "profile_path": "/5XBzD5WuTyVQZeS4VI25z2moMeY.jpg",
            "order": 0,
        },
        {
            "id": 287,
            "name": "Brad Pitt",
            "character": "Tyler Durden",
            "profile_path": "/cckcYc2v0yh1tc9QjRelptcOBko.jpg",
            "order": 1,
        },
    ],
    "crew": [
        {
            "id": 7467,
            "name": "David Fincher",
            "job": "Director",
            "department": "Directing",
            "profile_path": "/dcBHejOsKvzVZVozWJAPzYthb8X.jpg",
        },
        {
            "id": 7468,
            "name": "Jim Uhls",
            "job": "Screenplay",
            "department": "Writing",
            "profile_path": None,
        },
    ],
}

FAKE_MOVIE_REVIEWS = {
    "id": 550,
    "page": 1,
    "total_results": 1,
    "total_pages": 1,
    "results": [
        {
            "author": "MovieFan42",
            "content": "One of the best movies ever made. The twist is incredible.",
            "author_details": {"rating": 9.0},
            "created_at": "2021-05-15T10:00:00Z",
            "id": "abc123",
            "url": "https://www.themoviedb.org/review/abc123",
        },
    ],
}

FAKE_POPULAR_MOVIES = {
    "page": 1,
    "total_results": 500,
    "total_pages": 25,
    "results": [
        {
            "id": 550,
            "title": "Fight Club",
            "overview": "An insomniac office worker...",
            "release_date": "1999-10-15",
            "vote_average": 8.4,
            "vote_count": 25000,
            "popularity": 50.5,
            "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
            "backdrop_path": "/hZkgoQYus5dXo3H8T7Uef6DNknx.jpg",
            "genre_ids": [18, 53],
            "original_language": "en",
            "adult": False,
        },
    ],
}

FAKE_TOP_RATED_MOVIES = {
    "page": 1,
    "total_results": 1000,
    "total_pages": 50,
    "results": [
        {
            "id": 278,
            "title": "The Shawshank Redemption",
            "overview": "Framed in the 1940s for the double murder of his wife and her lover.",
            "release_date": "1994-09-23",
            "vote_average": 8.7,
            "vote_count": 23000,
            "popularity": 70.1,
            "poster_path": "/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg",
            "backdrop_path": "/kXfqcdQKsToO0OUXHcrrNCHDBzO.jpg",
            "genre_ids": [18, 80],
            "original_language": "en",
            "adult": False,
        },
    ],
}

FAKE_DISCOVER_MOVIES = {
    "page": 1,
    "total_results": 100,
    "total_pages": 5,
    "results": [
        {
            "id": 550,
            "title": "Fight Club",
            "overview": "An insomniac office worker...",
            "release_date": "1999-10-15",
            "vote_average": 8.4,
            "vote_count": 25000,
            "popularity": 50.5,
            "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
            "backdrop_path": "/hZkgoQYus5dXo3H8T7Uef6DNknx.jpg",
            "genre_ids": [18, 53],
            "original_language": "en",
            "adult": False,
        },
    ],
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/search/movie": FAKE_SEARCH_MOVIES,
        "/search/tv": FAKE_SEARCH_TV,
        "/movie/550": FAKE_MOVIE_DETAIL,
        "/tv/1396": FAKE_TV_DETAIL,
        "/trending/all/day": FAKE_TRENDING,
        "/trending/movie/week": FAKE_TRENDING,
        "/movie/550/credits": FAKE_MOVIE_CREDITS,
        "/movie/550/reviews": FAKE_MOVIE_REVIEWS,
        "/movie/popular": FAKE_POPULAR_MOVIES,
        "/movie/top_rated": FAKE_TOP_RATED_MOVIES,
        "/discover/movie": FAKE_DISCOVER_MOVIES,
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
    """TMDBService with mocked HTTP client."""
    from tmdb_mcp.service import TMDBService

    svc = TMDBService.__new__(TMDBService)
    svc._http = mock_http
    svc._api_key = "fake-api-key"
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked TMDBService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-tmdb", version="0.0.1")
    srv.register(service)
    return srv
