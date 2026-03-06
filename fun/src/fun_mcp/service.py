"""FunService — wraps several fun free APIs into proto RPCs."""

from __future__ import annotations

import html
from typing import Any

import httpx

from fun_mcp.gen.fun.v1 import fun_pb2 as pb

_DAD_JOKE_BASE = "https://icanhazdadjoke.com"
_TRIVIA_BASE = "https://opentdb.com"
_QUOTE_BASE = "https://api.quotable.io"
_DOG_BASE = "https://dog.ceo/api"
_CAT_FACT_BASE = "https://catfact.ninja"


class FunService:
    """Implements FunService RPCs via free public APIs."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, url: str, params: dict | None = None, headers: dict | None = None) -> Any:
        resp = self._http.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def GetDadJoke(self, request: Any, context: Any = None) -> pb.GetDadJokeResponse:
        raw = self._get(
            _DAD_JOKE_BASE,
            headers={"Accept": "application/json", "User-Agent": "FunMCP (https://github.com/jim-technologies)"},
        )
        return pb.GetDadJokeResponse(
            joke=pb.DadJoke(
                id=raw.get("id", ""),
                joke=raw.get("joke", ""),
                status=raw.get("status", 0),
            )
        )

    def SearchDadJokes(self, request: Any, context: Any = None) -> pb.SearchDadJokesResponse:
        params = {"term": request.query}
        if request.limit:
            params["limit"] = request.limit
        raw = self._get(
            f"{_DAD_JOKE_BASE}/search",
            params=params,
            headers={"Accept": "application/json", "User-Agent": "FunMCP (https://github.com/jim-technologies)"},
        )
        resp = pb.SearchDadJokesResponse(
            total=raw.get("total_jokes", 0),
        )
        for j in raw.get("results", []):
            resp.jokes.append(pb.DadJoke(
                id=j.get("id", ""),
                joke=j.get("joke", ""),
            ))
        return resp

    def GetTrivia(self, request: Any, context: Any = None) -> pb.GetTriviaResponse:
        params: dict[str, Any] = {"amount": request.amount or 1}
        if request.category:
            params["category"] = request.category
        if request.difficulty:
            params["difficulty"] = request.difficulty
        if request.type:
            params["type"] = request.type
        raw = self._get(f"{_TRIVIA_BASE}/api.php", params=params)
        resp = pb.GetTriviaResponse()
        for q in raw.get("results", []):
            resp.questions.append(pb.TriviaQuestion(
                category=html.unescape(q.get("category", "")),
                type=q.get("type", ""),
                difficulty=q.get("difficulty", ""),
                question=html.unescape(q.get("question", "")),
                correct_answer=html.unescape(q.get("correct_answer", "")),
                incorrect_answers=[html.unescape(a) for a in q.get("incorrect_answers", [])],
            ))
        return resp

    def GetTriviaCategories(self, request: Any, context: Any = None) -> pb.GetTriviaCategoriesResponse:
        raw = self._get(f"{_TRIVIA_BASE}/api_category.php")
        resp = pb.GetTriviaCategoriesResponse()
        for cat in raw.get("trivia_categories", []):
            resp.categories.append(pb.TriviaCategory(
                id=cat.get("id", 0),
                name=cat.get("name", ""),
            ))
        return resp

    def GetRandomQuote(self, request: Any, context: Any = None) -> pb.GetRandomQuoteResponse:
        raw = self._get(f"{_QUOTE_BASE}/quotes/random")
        # API returns a list with one element
        q = raw[0] if isinstance(raw, list) and raw else raw
        return pb.GetRandomQuoteResponse(
            quote=pb.Quote(
                id=q.get("_id", ""),
                content=q.get("content", ""),
                author=q.get("author", ""),
                tags=q.get("tags", []),
                length=q.get("length", 0),
            )
        )

    def SearchQuotes(self, request: Any, context: Any = None) -> pb.SearchQuotesResponse:
        raw = self._get(f"{_QUOTE_BASE}/search/quotes", params={"query": request.query})
        resp = pb.SearchQuotesResponse(
            total=raw.get("totalCount", 0),
        )
        for q in raw.get("results", []):
            resp.quotes.append(pb.Quote(
                id=q.get("_id", ""),
                content=q.get("content", ""),
                author=q.get("author", ""),
                tags=q.get("tags", []),
                length=q.get("length", 0),
            ))
        return resp

    def GetRandomDogImage(self, request: Any, context: Any = None) -> pb.GetRandomDogImageResponse:
        raw = self._get(f"{_DOG_BASE}/breeds/image/random")
        return pb.GetRandomDogImageResponse(
            image_url=raw.get("message", ""),
        )

    def GetDogImageByBreed(self, request: Any, context: Any = None) -> pb.GetDogImageByBreedResponse:
        raw = self._get(f"{_DOG_BASE}/breed/{request.breed}/images/random")
        return pb.GetDogImageByBreedResponse(
            image_url=raw.get("message", ""),
        )

    def ListDogBreeds(self, request: Any, context: Any = None) -> pb.ListDogBreedsResponse:
        raw = self._get(f"{_DOG_BASE}/breeds/list/all")
        resp = pb.ListDogBreedsResponse()
        for breed, sub_breeds in raw.get("message", {}).items():
            resp.breeds.append(pb.DogBreed(
                breed=breed,
                sub_breeds=sub_breeds or [],
            ))
        return resp

    def GetRandomCatFact(self, request: Any, context: Any = None) -> pb.GetRandomCatFactResponse:
        raw = self._get(f"{_CAT_FACT_BASE}/fact")
        return pb.GetRandomCatFactResponse(
            fact=raw.get("fact", ""),
            length=raw.get("length", 0),
        )
