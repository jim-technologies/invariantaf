"""Unit tests — every FunService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from fun_mcp.gen.fun.v1 import fun_pb2 as pb
from tests.conftest import (
    FAKE_CAT_FACT,
    FAKE_DAD_JOKE,
    FAKE_DAD_JOKE_SEARCH,
    FAKE_DOG_BREEDS,
    FAKE_DOG_BY_BREED,
    FAKE_RANDOM_DOG,
    FAKE_RANDOM_QUOTE,
    FAKE_SEARCH_QUOTES,
    FAKE_TRIVIA,
    FAKE_TRIVIA_CATEGORIES,
)


class TestGetDadJoke:
    def test_returns_joke(self, service):
        resp = service.GetDadJoke(pb.GetDadJokeRequest())
        assert resp.joke.id == "R7UfaahVfFd"
        assert "bike" in resp.joke.joke
        assert resp.joke.status == 200

    def test_sends_correct_headers(self, service, mock_http):
        service.GetDadJoke(pb.GetDadJokeRequest())
        call_args = mock_http.get.call_args
        headers = call_args[1].get("headers", {})
        assert headers.get("Accept") == "application/json"
        assert "User-Agent" in headers

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None, headers=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetDadJoke(pb.GetDadJokeRequest())
        assert resp.joke.id == ""
        assert resp.joke.joke == ""


class TestSearchDadJokes:
    def test_returns_jokes(self, service):
        resp = service.SearchDadJokes(pb.SearchDadJokesRequest(query="noodle"))
        assert len(resp.jokes) == 2
        assert resp.total == 2

    def test_first_joke(self, service):
        resp = service.SearchDadJokes(pb.SearchDadJokesRequest(query="noodle"))
        assert resp.jokes[0].id == "abc123"
        assert "impasta" in resp.jokes[0].joke

    def test_second_joke(self, service):
        resp = service.SearchDadJokes(pb.SearchDadJokesRequest(query="facial"))
        assert resp.jokes[1].id == "def456"
        assert "facial hair" in resp.jokes[1].joke

    def test_with_limit(self, service, mock_http):
        service.SearchDadJokes(pb.SearchDadJokesRequest(query="test", limit=5))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("limit") == 5


class TestGetTrivia:
    def test_returns_questions(self, service):
        resp = service.GetTrivia(pb.GetTriviaRequest(amount=2))
        assert len(resp.questions) == 2

    def test_first_question(self, service):
        resp = service.GetTrivia(pb.GetTriviaRequest(amount=2))
        q = resp.questions[0]
        assert q.category == "Science & Nature"
        assert q.type == "multiple"
        assert q.difficulty == "medium"
        assert "gold" in q.question
        assert q.correct_answer == "Au"
        assert len(q.incorrect_answers) == 3

    def test_boolean_question(self, service):
        resp = service.GetTrivia(pb.GetTriviaRequest(amount=2))
        q = resp.questions[1]
        assert q.type == "boolean"
        assert q.correct_answer == "False"
        assert len(q.incorrect_answers) == 1

    def test_html_unescaping(self, service):
        resp = service.GetTrivia(pb.GetTriviaRequest(amount=2))
        # "Science &amp; Nature" should be unescaped to "Science & Nature"
        assert "&amp;" not in resp.questions[0].category

    def test_with_category_filter(self, service, mock_http):
        service.GetTrivia(pb.GetTriviaRequest(amount=1, category=18))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("category") == 18

    def test_with_difficulty_filter(self, service, mock_http):
        service.GetTrivia(pb.GetTriviaRequest(amount=1, difficulty="hard"))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("difficulty") == "hard"


class TestGetTriviaCategories:
    def test_returns_categories(self, service):
        resp = service.GetTriviaCategories(pb.GetTriviaCategoriesRequest())
        assert len(resp.categories) == 5

    def test_category_fields(self, service):
        resp = service.GetTriviaCategories(pb.GetTriviaCategoriesRequest())
        assert resp.categories[0].id == 9
        assert resp.categories[0].name == "General Knowledge"
        assert resp.categories[1].id == 18
        assert resp.categories[1].name == "Science: Computers"

    def test_all_categories_present(self, service):
        resp = service.GetTriviaCategories(pb.GetTriviaCategoriesRequest())
        names = [c.name for c in resp.categories]
        assert "Sports" in names
        assert "Geography" in names
        assert "History" in names


class TestGetRandomQuote:
    def test_returns_quote(self, service):
        resp = service.GetRandomQuote(pb.GetRandomQuoteRequest())
        assert resp.quote.id == "q1abc"
        assert "great work" in resp.quote.content
        assert resp.quote.author == "Steve Jobs"

    def test_quote_tags(self, service):
        resp = service.GetRandomQuote(pb.GetRandomQuoteRequest())
        assert "inspirational" in resp.quote.tags
        assert "work" in resp.quote.tags

    def test_quote_length(self, service):
        resp = service.GetRandomQuote(pb.GetRandomQuoteRequest())
        assert resp.quote.length == 52


class TestSearchQuotes:
    def test_returns_quotes(self, service):
        resp = service.SearchQuotes(pb.SearchQuotesRequest(query="opportunity"))
        assert len(resp.quotes) == 2
        assert resp.total == 2

    def test_first_quote(self, service):
        resp = service.SearchQuotes(pb.SearchQuotesRequest(query="opportunity"))
        q = resp.quotes[0]
        assert q.id == "q2def"
        assert "difficulty" in q.content
        assert q.author == "Albert Einstein"
        assert "wisdom" in q.tags

    def test_second_quote(self, service):
        resp = service.SearchQuotes(pb.SearchQuotesRequest(query="life"))
        q = resp.quotes[1]
        assert q.id == "q3ghi"
        assert q.author == "John Lennon"
        assert q.length == 56


class TestGetRandomDogImage:
    def test_returns_image_url(self, service):
        resp = service.GetRandomDogImage(pb.GetRandomDogImageRequest())
        assert "labrador" in resp.image_url
        assert resp.image_url.startswith("https://")

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None, headers=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetRandomDogImage(pb.GetRandomDogImageRequest())
        assert resp.image_url == ""


class TestGetDogImageByBreed:
    def test_returns_image_url(self, service):
        resp = service.GetDogImageByBreed(pb.GetDogImageByBreedRequest(breed="husky"))
        assert "husky" in resp.image_url
        assert resp.image_url.startswith("https://")

    def test_sends_breed_in_url(self, service, mock_http):
        service.GetDogImageByBreed(pb.GetDogImageByBreedRequest(breed="husky"))
        call_args = mock_http.get.call_args
        assert "husky" in call_args[0][0]


class TestListDogBreeds:
    def test_returns_breeds(self, service):
        resp = service.ListDogBreeds(pb.ListDogBreedsRequest())
        assert len(resp.breeds) == 4

    def test_breed_names(self, service):
        resp = service.ListDogBreeds(pb.ListDogBreedsRequest())
        breed_names = [b.breed for b in resp.breeds]
        assert "labrador" in breed_names
        assert "poodle" in breed_names
        assert "husky" in breed_names
        assert "corgi" in breed_names

    def test_sub_breeds(self, service):
        resp = service.ListDogBreeds(pb.ListDogBreedsRequest())
        poodle = [b for b in resp.breeds if b.breed == "poodle"][0]
        assert len(poodle.sub_breeds) == 3
        assert "standard" in poodle.sub_breeds
        assert "miniature" in poodle.sub_breeds
        assert "toy" in poodle.sub_breeds

    def test_no_sub_breeds(self, service):
        resp = service.ListDogBreeds(pb.ListDogBreedsRequest())
        labrador = [b for b in resp.breeds if b.breed == "labrador"][0]
        assert len(labrador.sub_breeds) == 0

    def test_corgi_sub_breeds(self, service):
        resp = service.ListDogBreeds(pb.ListDogBreedsRequest())
        corgi = [b for b in resp.breeds if b.breed == "corgi"][0]
        assert len(corgi.sub_breeds) == 1
        assert "cardigan" in corgi.sub_breeds


class TestGetRandomCatFact:
    def test_returns_fact(self, service):
        resp = service.GetRandomCatFact(pb.GetRandomCatFactRequest())
        assert "vocalizations" in resp.fact
        assert resp.length == 70

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None, headers=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetRandomCatFact(pb.GetRandomCatFactRequest())
        assert resp.fact == ""
        assert resp.length == 0
