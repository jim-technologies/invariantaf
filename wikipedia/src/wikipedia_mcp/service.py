"""WikipediaService — wraps the Wikipedia REST and Action APIs into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from wikipedia_mcp.gen.wikipedia.v1 import wikipedia_pb2 as pb

_REST_BASE = "https://en.wikipedia.org/api/rest_v1"
_ACTION_BASE = "https://en.wikipedia.org/w/api.php"
_USER_AGENT = "InvariantMCP/0.1 (https://github.com/jim-technologies/invariantaf)"


class WikipediaService:
    """Implements WikipediaService RPCs via the free Wikipedia APIs."""

    def __init__(self):
        self._http = httpx.Client(
            timeout=30,
            headers={"User-Agent": _USER_AGENT},
        )

    def _rest_get(self, path: str) -> Any:
        resp = self._http.get(f"{_REST_BASE}{path}")
        resp.raise_for_status()
        return resp.json()

    def _action_get(self, params: dict) -> Any:
        params["format"] = "json"
        resp = self._http.get(_ACTION_BASE, params=params)
        resp.raise_for_status()
        return resp.json()

    def Search(self, request: Any, context: Any = None) -> pb.SearchResponse:
        limit = request.limit or 10
        raw = self._action_get({
            "action": "query",
            "list": "search",
            "srsearch": request.query,
            "srlimit": str(limit),
        })
        resp = pb.SearchResponse()
        search_data = raw.get("query", {}).get("search", [])
        resp.total_hits = raw.get("query", {}).get("searchinfo", {}).get("totalhits", 0)
        for item in search_data:
            resp.results.append(pb.SearchResult(
                page_id=item.get("pageid", 0),
                title=item.get("title", ""),
                snippet=item.get("snippet", ""),
                word_count=item.get("wordcount", 0),
                timestamp=item.get("timestamp", ""),
            ))
        return resp

    def GetPage(self, request: Any, context: Any = None) -> pb.GetPageResponse:
        raw = self._rest_get(f"/page/summary/{request.title}")
        thumbnail = raw.get("thumbnail", {}) or {}
        content_urls = raw.get("content_urls", {}) or {}
        desktop = content_urls.get("desktop", {}) or {}
        return pb.GetPageResponse(
            title=raw.get("title", ""),
            extract=raw.get("extract", ""),
            thumbnail_url=thumbnail.get("source", ""),
            description=raw.get("description", ""),
            page_id=raw.get("pageid", 0),
            content_url=desktop.get("page", ""),
        )

    def GetFullPage(self, request: Any, context: Any = None) -> pb.GetFullPageResponse:
        raw = self._action_get({
            "action": "query",
            "prop": "extracts",
            "explaintext": "true",
            "titles": request.title,
        })
        pages = raw.get("query", {}).get("pages", {})
        # pages is a dict keyed by page ID
        for page_id, page_data in pages.items():
            return pb.GetFullPageResponse(
                title=page_data.get("title", ""),
                content=page_data.get("extract", ""),
                page_id=int(page_id) if page_id != "-1" else 0,
            )
        return pb.GetFullPageResponse()

    def GetRandom(self, request: Any, context: Any = None) -> pb.GetRandomResponse:
        count = request.count or 1
        resp = pb.GetRandomResponse()
        for _ in range(count):
            raw = self._rest_get("/page/random/summary")
            thumbnail = raw.get("thumbnail", {}) or {}
            content_urls = raw.get("content_urls", {}) or {}
            desktop = content_urls.get("desktop", {}) or {}
            resp.pages.append(pb.PageSummary(
                title=raw.get("title", ""),
                extract=raw.get("extract", ""),
                thumbnail_url=thumbnail.get("source", ""),
                description=raw.get("description", ""),
                page_id=raw.get("pageid", 0),
                content_url=desktop.get("page", ""),
            ))
        return resp

    def GetOnThisDay(self, request: Any, context: Any = None) -> pb.GetOnThisDayResponse:
        mm = f"{request.month:02d}"
        dd = f"{request.day:02d}"
        raw = self._rest_get(f"/feed/onthisday/events/{mm}/{dd}")
        resp = pb.GetOnThisDayResponse()
        for event in raw.get("events", []):
            pages = []
            for p in event.get("pages", []):
                thumbnail = p.get("thumbnail", {}) or {}
                content_urls = p.get("content_urls", {}) or {}
                desktop = content_urls.get("desktop", {}) or {}
                pages.append(pb.PageSummary(
                    title=p.get("title", ""),
                    extract=p.get("extract", ""),
                    thumbnail_url=thumbnail.get("source", ""),
                    description=p.get("description", ""),
                    page_id=p.get("pageid", 0),
                    content_url=desktop.get("page", ""),
                ))
            resp.events.append(pb.OnThisDayEvent(
                year=event.get("year", 0),
                text=event.get("text", ""),
                pages=pages,
            ))
        return resp

    def GetMostRead(self, request: Any, context: Any = None) -> pb.GetMostReadResponse:
        yyyy = f"{request.year:04d}"
        mm = f"{request.month:02d}"
        dd = f"{request.day:02d}"
        raw = self._rest_get(f"/feed/featured/{yyyy}/{mm}/{dd}")
        most_read = raw.get("mostread", {}) or {}
        resp = pb.GetMostReadResponse()
        resp.date = most_read.get("date", "")
        for article in most_read.get("articles", []):
            thumbnail = article.get("thumbnail", {}) or {}
            resp.articles.append(pb.MostReadArticle(
                title=article.get("title", ""),
                views=article.get("views", 0),
                extract=article.get("extract", ""),
                thumbnail_url=thumbnail.get("source", ""),
                description=article.get("description", ""),
            ))
        return resp

    def GetLanguages(self, request: Any, context: Any = None) -> pb.GetLanguagesResponse:
        raw = self._action_get({
            "action": "query",
            "prop": "langlinks",
            "titles": request.title,
            "lllimit": "500",
        })
        pages = raw.get("query", {}).get("pages", {})
        resp = pb.GetLanguagesResponse()
        for page_data in pages.values():
            for ll in page_data.get("langlinks", []):
                resp.languages.append(pb.LanguageLink(
                    lang=ll.get("lang", ""),
                    title=ll.get("*", ""),
                ))
        return resp

    def GetCategories(self, request: Any, context: Any = None) -> pb.GetCategoriesResponse:
        raw = self._action_get({
            "action": "query",
            "prop": "categories",
            "titles": request.title,
            "cllimit": "500",
        })
        pages = raw.get("query", {}).get("pages", {})
        resp = pb.GetCategoriesResponse()
        for page_data in pages.values():
            for cat in page_data.get("categories", []):
                resp.categories.append(cat.get("title", ""))
        return resp

    def GetLinks(self, request: Any, context: Any = None) -> pb.GetLinksResponse:
        raw = self._action_get({
            "action": "query",
            "prop": "links",
            "titles": request.title,
            "pllimit": "500",
        })
        pages = raw.get("query", {}).get("pages", {})
        resp = pb.GetLinksResponse()
        for page_data in pages.values():
            for link in page_data.get("links", []):
                resp.links.append(link.get("title", ""))
        return resp

    def GetImages(self, request: Any, context: Any = None) -> pb.GetImagesResponse:
        raw = self._action_get({
            "action": "query",
            "prop": "images",
            "titles": request.title,
            "imlimit": "500",
        })
        pages = raw.get("query", {}).get("pages", {})
        resp = pb.GetImagesResponse()
        for page_data in pages.values():
            for img in page_data.get("images", []):
                resp.images.append(img.get("title", ""))
        return resp
