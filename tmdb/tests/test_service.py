"""Unit tests — every TMDBService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from tmdb_mcp.gen.tmdb.v1 import tmdb_pb2 as pb
from tests.conftest import (
    FAKE_SEARCH_MOVIES,
    FAKE_SEARCH_TV,
    FAKE_MOVIE_DETAIL,
    FAKE_TV_DETAIL,
    FAKE_TRENDING,
    FAKE_MOVIE_CREDITS,
    FAKE_MOVIE_REVIEWS,
    FAKE_POPULAR_MOVIES,
    FAKE_TOP_RATED_MOVIES,
    FAKE_DISCOVER_MOVIES,
)


class TestSearchMovies:
    def test_returns_movies(self, service):
        resp = service.SearchMovies(pb.SearchMoviesRequest(query="fight club"))
        assert len(resp.results) == 2
        assert resp.total_results == 2
        assert resp.total_pages == 1
        assert resp.page == 1

    def test_first_movie_fields(self, service):
        resp = service.SearchMovies(pb.SearchMoviesRequest(query="fight club"))
        m = resp.results[0]
        assert m.id == 550
        assert m.title == "Fight Club"
        assert "insomniac" in m.overview
        assert m.release_date == "1999-10-15"
        assert m.vote_average == 8.4
        assert m.vote_count == 25000
        assert m.poster_path == "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg"
        assert 18 in m.genre_ids
        assert 53 in m.genre_ids

    def test_second_movie(self, service):
        resp = service.SearchMovies(pb.SearchMoviesRequest(query="pulp"))
        m = resp.results[1]
        assert m.id == 680
        assert m.title == "Pulp Fiction"
        assert m.vote_average == 8.5

    def test_with_year_filter(self, service, mock_http):
        service.SearchMovies(pb.SearchMoviesRequest(query="fight", year=1999))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("year") == 1999

    def test_empty_results(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"page": 1, "total_results": 0, "total_pages": 0, "results": []}),
        )
        resp = service.SearchMovies(pb.SearchMoviesRequest(query="nonexistent"))
        assert len(resp.results) == 0
        assert resp.total_results == 0


class TestSearchTV:
    def test_returns_tv_shows(self, service):
        resp = service.SearchTV(pb.SearchTVRequest(query="breaking bad"))
        assert len(resp.results) == 1
        assert resp.total_results == 1
        assert resp.page == 1

    def test_tv_show_fields(self, service):
        resp = service.SearchTV(pb.SearchTVRequest(query="breaking bad"))
        t = resp.results[0]
        assert t.id == 1396
        assert t.name == "Breaking Bad"
        assert "chemistry teacher" in t.overview
        assert t.first_air_date == "2008-01-20"
        assert t.vote_average == 8.9
        assert t.vote_count == 12000
        assert t.poster_path == "/ggFHVNu6YYI5L9pCfOacjizRGt.jpg"
        assert 18 in t.genre_ids
        assert 80 in t.genre_ids

    def test_with_year_filter(self, service, mock_http):
        service.SearchTV(pb.SearchTVRequest(query="breaking", first_air_date_year=2008))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("first_air_date_year") == 2008


class TestGetMovie:
    def test_basic_fields(self, service):
        resp = service.GetMovie(pb.GetMovieRequest(id=550))
        assert resp.id == 550
        assert resp.title == "Fight Club"
        assert "insomniac" in resp.overview
        assert resp.release_date == "1999-10-15"
        assert resp.vote_average == 8.4
        assert resp.vote_count == 25000

    def test_genres(self, service):
        resp = service.GetMovie(pb.GetMovieRequest(id=550))
        assert len(resp.genres) == 2
        names = [g.name for g in resp.genres]
        assert "Drama" in names
        assert "Thriller" in names

    def test_production_fields(self, service):
        resp = service.GetMovie(pb.GetMovieRequest(id=550))
        assert resp.runtime == 139
        assert resp.budget == 63000000
        assert resp.revenue == 100853753

    def test_metadata_fields(self, service):
        resp = service.GetMovie(pb.GetMovieRequest(id=550))
        assert resp.poster_path == "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg"
        assert resp.tagline == "Mischief. Mayhem. Soap."
        assert resp.status == "Released"
        assert resp.original_language == "en"
        assert resp.imdb_id == "tt0137523"

    def test_homepage(self, service):
        resp = service.GetMovie(pb.GetMovieRequest(id=550))
        assert "foxmovies" in resp.homepage


class TestGetTVShow:
    def test_basic_fields(self, service):
        resp = service.GetTVShow(pb.GetTVShowRequest(id=1396))
        assert resp.id == 1396
        assert resp.name == "Breaking Bad"
        assert "chemistry teacher" in resp.overview
        assert resp.first_air_date == "2008-01-20"
        assert resp.vote_average == 8.9

    def test_genres(self, service):
        resp = service.GetTVShow(pb.GetTVShowRequest(id=1396))
        assert len(resp.genres) == 2
        names = [g.name for g in resp.genres]
        assert "Drama" in names
        assert "Crime" in names

    def test_seasons_and_episodes(self, service):
        resp = service.GetTVShow(pb.GetTVShowRequest(id=1396))
        assert resp.number_of_seasons == 5
        assert resp.number_of_episodes == 62

    def test_status(self, service):
        resp = service.GetTVShow(pb.GetTVShowRequest(id=1396))
        assert resp.status == "Ended"
        assert resp.type == "Scripted"

    def test_metadata(self, service):
        resp = service.GetTVShow(pb.GetTVShowRequest(id=1396))
        assert resp.tagline == "Remember my name."
        assert "amc.com" in resp.homepage


class TestGetTrending:
    def test_returns_trending_items(self, service):
        resp = service.GetTrending(pb.GetTrendingRequest())
        assert len(resp.results) == 2
        assert resp.total_results == 2
        assert resp.page == 1

    def test_movie_trending_item(self, service):
        resp = service.GetTrending(pb.GetTrendingRequest())
        item = resp.results[0]
        assert item.id == 550
        assert item.title == "Fight Club"
        assert item.media_type == "movie"
        assert item.vote_average == 8.4

    def test_tv_trending_item(self, service):
        resp = service.GetTrending(pb.GetTrendingRequest())
        item = resp.results[1]
        assert item.id == 1396
        assert item.name == "Breaking Bad"
        assert item.media_type == "tv"
        assert item.first_air_date == "2008-01-20"

    def test_custom_params(self, service, mock_http):
        service.GetTrending(pb.GetTrendingRequest(media_type="movie", time_window="week"))
        call_args = mock_http.get.call_args
        url = call_args[0][0] if call_args[0] else ""
        assert "/trending/movie/week" in url


class TestGetMovieCredits:
    def test_returns_cast(self, service):
        resp = service.GetMovieCredits(pb.GetMovieCreditsRequest(id=550))
        assert resp.id == 550
        assert len(resp.cast) == 2

    def test_cast_fields(self, service):
        resp = service.GetMovieCredits(pb.GetMovieCreditsRequest(id=550))
        norton = resp.cast[0]
        assert norton.id == 819
        assert norton.name == "Edward Norton"
        assert norton.character == "The Narrator"
        assert norton.order == 0

    def test_second_cast_member(self, service):
        resp = service.GetMovieCredits(pb.GetMovieCreditsRequest(id=550))
        pitt = resp.cast[1]
        assert pitt.id == 287
        assert pitt.name == "Brad Pitt"
        assert pitt.character == "Tyler Durden"
        assert pitt.order == 1

    def test_crew(self, service):
        resp = service.GetMovieCredits(pb.GetMovieCreditsRequest(id=550))
        assert len(resp.crew) == 2
        director = resp.crew[0]
        assert director.name == "David Fincher"
        assert director.job == "Director"
        assert director.department == "Directing"

    def test_crew_with_null_profile(self, service):
        resp = service.GetMovieCredits(pb.GetMovieCreditsRequest(id=550))
        writer = resp.crew[1]
        assert writer.name == "Jim Uhls"
        assert writer.profile_path == ""


class TestGetMovieReviews:
    def test_returns_reviews(self, service):
        resp = service.GetMovieReviews(pb.GetMovieReviewsRequest(id=550))
        assert resp.id == 550
        assert len(resp.results) == 1
        assert resp.total_results == 1

    def test_review_fields(self, service):
        resp = service.GetMovieReviews(pb.GetMovieReviewsRequest(id=550))
        r = resp.results[0]
        assert r.author == "MovieFan42"
        assert "best movies ever" in r.content
        assert r.rating == 9.0
        assert r.created_at == "2021-05-15T10:00:00Z"
        assert r.id == "abc123"
        assert "themoviedb.org" in r.url


class TestGetPopularMovies:
    def test_returns_popular(self, service):
        resp = service.GetPopularMovies(pb.GetPopularMoviesRequest())
        assert len(resp.results) == 1
        assert resp.total_results == 500
        assert resp.total_pages == 25

    def test_movie_fields(self, service):
        resp = service.GetPopularMovies(pb.GetPopularMoviesRequest())
        m = resp.results[0]
        assert m.id == 550
        assert m.title == "Fight Club"
        assert m.vote_average == 8.4

    def test_with_page(self, service, mock_http):
        service.GetPopularMovies(pb.GetPopularMoviesRequest(page=2))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("page") == 2


class TestGetTopRatedMovies:
    def test_returns_top_rated(self, service):
        resp = service.GetTopRatedMovies(pb.GetTopRatedMoviesRequest())
        assert len(resp.results) == 1
        assert resp.total_results == 1000
        assert resp.total_pages == 50

    def test_movie_fields(self, service):
        resp = service.GetTopRatedMovies(pb.GetTopRatedMoviesRequest())
        m = resp.results[0]
        assert m.id == 278
        assert m.title == "The Shawshank Redemption"
        assert m.vote_average == 8.7
        assert m.release_date == "1994-09-23"


class TestGetDiscoverMovies:
    def test_returns_discover_results(self, service):
        resp = service.DiscoverMovies(pb.DiscoverMoviesRequest())
        assert len(resp.results) == 1
        assert resp.total_results == 100
        assert resp.total_pages == 5

    def test_movie_fields(self, service):
        resp = service.DiscoverMovies(pb.DiscoverMoviesRequest())
        m = resp.results[0]
        assert m.id == 550
        assert m.title == "Fight Club"
        assert m.vote_average == 8.4

    def test_with_filters(self, service, mock_http):
        service.DiscoverMovies(pb.DiscoverMoviesRequest(
            year=1999,
            with_genres="18",
            sort_by="vote_average.desc",
            vote_average_gte=8.0,
            vote_count_gte=1000,
        ))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("year") == 1999
        assert params.get("with_genres") == "18"
        assert params.get("sort_by") == "vote_average.desc"
        assert params.get("vote_average.gte") == 8.0
        assert params.get("vote_count.gte") == 1000

    def test_default_sort(self, service, mock_http):
        service.DiscoverMovies(pb.DiscoverMoviesRequest())
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("sort_by") == "popularity.desc"
