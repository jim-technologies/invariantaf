"""TMDBService — wraps the TMDB API v3 into proto RPCs."""

from __future__ import annotations

import os
from typing import Any

import httpx

from tmdb_mcp.gen.tmdb.v1 import tmdb_pb2 as pb

_BASE_URL = "https://api.themoviedb.org/3"


class TMDBService:
    """Implements TMDBService RPCs via the TMDB API v3."""

    def __init__(self, *, api_key: str | None = None):
        self._http = httpx.Client(timeout=30)
        self._api_key = api_key or os.environ.get("TMDB_API_KEY")
        if not self._api_key:
            raise ValueError(
                "TMDB API key is required. Set TMDB_API_KEY env var or pass api_key."
            )

    def _get(self, path: str, params: dict | None = None) -> Any:
        p = dict(params or {})
        p["api_key"] = self._api_key
        resp = self._http.get(f"{_BASE_URL}{path}", params=p)
        resp.raise_for_status()
        return resp.json()

    def _parse_movie(self, m: dict) -> pb.Movie:
        return pb.Movie(
            id=m.get("id", 0),
            title=m.get("title", ""),
            overview=m.get("overview", ""),
            release_date=m.get("release_date", "") or "",
            vote_average=m.get("vote_average", 0) or 0,
            vote_count=m.get("vote_count", 0) or 0,
            popularity=m.get("popularity", 0) or 0,
            poster_path=m.get("poster_path", "") or "",
            backdrop_path=m.get("backdrop_path", "") or "",
            genre_ids=m.get("genre_ids", []) or [],
            original_language=m.get("original_language", ""),
            adult=m.get("adult", False),
        )

    def _parse_tv(self, t: dict) -> pb.TVShow:
        return pb.TVShow(
            id=t.get("id", 0),
            name=t.get("name", ""),
            overview=t.get("overview", ""),
            first_air_date=t.get("first_air_date", "") or "",
            vote_average=t.get("vote_average", 0) or 0,
            vote_count=t.get("vote_count", 0) or 0,
            popularity=t.get("popularity", 0) or 0,
            poster_path=t.get("poster_path", "") or "",
            backdrop_path=t.get("backdrop_path", "") or "",
            genre_ids=t.get("genre_ids", []) or [],
            original_language=t.get("original_language", ""),
        )

    def SearchMovies(self, request: Any, context: Any = None) -> pb.SearchMoviesResponse:
        params: dict[str, Any] = {"query": request.query}
        if request.page:
            params["page"] = request.page
        if request.year:
            params["year"] = request.year

        raw = self._get("/search/movie", params)
        resp = pb.SearchMoviesResponse(
            total_results=raw.get("total_results", 0),
            total_pages=raw.get("total_pages", 0),
            page=raw.get("page", 0),
        )
        for m in raw.get("results", []):
            resp.results.append(self._parse_movie(m))
        return resp

    def SearchTV(self, request: Any, context: Any = None) -> pb.SearchTVResponse:
        params: dict[str, Any] = {"query": request.query}
        if request.page:
            params["page"] = request.page
        if request.first_air_date_year:
            params["first_air_date_year"] = request.first_air_date_year

        raw = self._get("/search/tv", params)
        resp = pb.SearchTVResponse(
            total_results=raw.get("total_results", 0),
            total_pages=raw.get("total_pages", 0),
            page=raw.get("page", 0),
        )
        for t in raw.get("results", []):
            resp.results.append(self._parse_tv(t))
        return resp

    def GetMovie(self, request: Any, context: Any = None) -> pb.GetMovieResponse:
        raw = self._get(f"/movie/{request.id}")
        genres = [
            pb.Genre(id=g.get("id", 0), name=g.get("name", ""))
            for g in raw.get("genres", [])
        ]
        return pb.GetMovieResponse(
            id=raw.get("id", 0),
            title=raw.get("title", ""),
            overview=raw.get("overview", ""),
            release_date=raw.get("release_date", "") or "",
            vote_average=raw.get("vote_average", 0) or 0,
            vote_count=raw.get("vote_count", 0) or 0,
            genres=genres,
            runtime=raw.get("runtime", 0) or 0,
            budget=raw.get("budget", 0) or 0,
            revenue=raw.get("revenue", 0) or 0,
            poster_path=raw.get("poster_path", "") or "",
            backdrop_path=raw.get("backdrop_path", "") or "",
            tagline=raw.get("tagline", "") or "",
            status=raw.get("status", ""),
            original_language=raw.get("original_language", ""),
            popularity=raw.get("popularity", 0) or 0,
            homepage=raw.get("homepage", "") or "",
            imdb_id=raw.get("imdb_id", "") or "",
        )

    def GetTVShow(self, request: Any, context: Any = None) -> pb.GetTVShowResponse:
        raw = self._get(f"/tv/{request.id}")
        genres = [
            pb.Genre(id=g.get("id", 0), name=g.get("name", ""))
            for g in raw.get("genres", [])
        ]
        return pb.GetTVShowResponse(
            id=raw.get("id", 0),
            name=raw.get("name", ""),
            overview=raw.get("overview", ""),
            first_air_date=raw.get("first_air_date", "") or "",
            vote_average=raw.get("vote_average", 0) or 0,
            vote_count=raw.get("vote_count", 0) or 0,
            genres=genres,
            number_of_seasons=raw.get("number_of_seasons", 0) or 0,
            number_of_episodes=raw.get("number_of_episodes", 0) or 0,
            status=raw.get("status", ""),
            poster_path=raw.get("poster_path", "") or "",
            backdrop_path=raw.get("backdrop_path", "") or "",
            tagline=raw.get("tagline", "") or "",
            original_language=raw.get("original_language", ""),
            popularity=raw.get("popularity", 0) or 0,
            homepage=raw.get("homepage", "") or "",
            type=raw.get("type", ""),
        )

    def GetTrending(self, request: Any, context: Any = None) -> pb.GetTrendingResponse:
        media_type = request.media_type or "all"
        time_window = request.time_window or "day"
        raw = self._get(f"/trending/{media_type}/{time_window}")
        resp = pb.GetTrendingResponse(
            total_results=raw.get("total_results", 0),
            total_pages=raw.get("total_pages", 0),
            page=raw.get("page", 0),
        )
        for item in raw.get("results", []):
            resp.results.append(pb.TrendingItem(
                id=item.get("id", 0),
                title=item.get("title", "") or "",
                name=item.get("name", "") or "",
                media_type=item.get("media_type", ""),
                overview=item.get("overview", "") or "",
                release_date=item.get("release_date", "") or "",
                first_air_date=item.get("first_air_date", "") or "",
                vote_average=item.get("vote_average", 0) or 0,
                poster_path=item.get("poster_path", "") or "",
                popularity=item.get("popularity", 0) or 0,
            ))
        return resp

    def GetMovieCredits(self, request: Any, context: Any = None) -> pb.GetMovieCreditsResponse:
        raw = self._get(f"/movie/{request.id}/credits")
        resp = pb.GetMovieCreditsResponse(id=raw.get("id", 0))
        for c in raw.get("cast", []):
            resp.cast.append(pb.CastMember(
                id=c.get("id", 0),
                name=c.get("name", ""),
                character=c.get("character", ""),
                profile_path=c.get("profile_path", "") or "",
                order=c.get("order", 0),
            ))
        for c in raw.get("crew", []):
            resp.crew.append(pb.CrewMember(
                id=c.get("id", 0),
                name=c.get("name", ""),
                job=c.get("job", ""),
                department=c.get("department", ""),
                profile_path=c.get("profile_path", "") or "",
            ))
        return resp

    def GetMovieReviews(self, request: Any, context: Any = None) -> pb.GetMovieReviewsResponse:
        params: dict[str, Any] = {}
        if request.page:
            params["page"] = request.page

        raw = self._get(f"/movie/{request.id}/reviews", params)
        resp = pb.GetMovieReviewsResponse(
            id=raw.get("id", 0),
            total_results=raw.get("total_results", 0),
            total_pages=raw.get("total_pages", 0),
            page=raw.get("page", 0),
        )
        for r in raw.get("results", []):
            details = r.get("author_details", {})
            resp.results.append(pb.Review(
                author=r.get("author", ""),
                content=r.get("content", ""),
                rating=details.get("rating", 0) or 0,
                created_at=r.get("created_at", ""),
                id=r.get("id", ""),
                url=r.get("url", ""),
            ))
        return resp

    def GetPopularMovies(self, request: Any, context: Any = None) -> pb.GetPopularMoviesResponse:
        params: dict[str, Any] = {}
        if request.page:
            params["page"] = request.page

        raw = self._get("/movie/popular", params)
        resp = pb.GetPopularMoviesResponse(
            total_results=raw.get("total_results", 0),
            total_pages=raw.get("total_pages", 0),
            page=raw.get("page", 0),
        )
        for m in raw.get("results", []):
            resp.results.append(self._parse_movie(m))
        return resp

    def GetTopRatedMovies(self, request: Any, context: Any = None) -> pb.GetTopRatedMoviesResponse:
        params: dict[str, Any] = {}
        if request.page:
            params["page"] = request.page

        raw = self._get("/movie/top_rated", params)
        resp = pb.GetTopRatedMoviesResponse(
            total_results=raw.get("total_results", 0),
            total_pages=raw.get("total_pages", 0),
            page=raw.get("page", 0),
        )
        for m in raw.get("results", []):
            resp.results.append(self._parse_movie(m))
        return resp

    def DiscoverMovies(self, request: Any, context: Any = None) -> pb.DiscoverMoviesResponse:
        params: dict[str, Any] = {
            "sort_by": request.sort_by or "popularity.desc",
        }
        if request.year:
            params["year"] = request.year
        if request.with_genres:
            params["with_genres"] = request.with_genres
        if request.vote_average_gte:
            params["vote_average.gte"] = request.vote_average_gte
        if request.page:
            params["page"] = request.page
        if request.vote_count_gte:
            params["vote_count.gte"] = request.vote_count_gte

        raw = self._get("/discover/movie", params)
        resp = pb.DiscoverMoviesResponse(
            total_results=raw.get("total_results", 0),
            total_pages=raw.get("total_pages", 0),
            page=raw.get("page", 0),
        )
        for m in raw.get("results", []):
            resp.results.append(self._parse_movie(m))
        return resp
