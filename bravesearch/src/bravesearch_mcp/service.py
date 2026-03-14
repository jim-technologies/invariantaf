"""Brave Search API service implementation for Invariant Protocol."""

from __future__ import annotations

import os
import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from bravesearch_mcp.gen.bravesearch.v1 import bravesearch_pb2 as pb

DEFAULT_BASE_URL = "https://api.search.brave.com/res/v1"


class BraveSearchService:
    """Implements BraveSearchService -- Brave Search API endpoints."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 15.0,
    ):
        self._base_url = (base_url or os.getenv("BRAVE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self._api_key = api_key or os.getenv("BRAVE_API_KEY") or ""
        self._timeout = timeout
        self._client = httpx.Client(
            timeout=timeout,
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self._api_key,
            },
        )

    # -------------------------
    # RPC handlers
    # -------------------------

    def WebSearch(
        self, request: pb.WebSearchRequest, context: Any = None
    ) -> pb.WebSearchResponse:
        query: dict[str, Any] = {"q": request.query}
        if request.count:
            query["count"] = request.count
        if request.offset:
            query["offset"] = request.offset
        if request.country:
            query["country"] = request.country
        if request.search_lang:
            query["search_lang"] = request.search_lang
        if request.freshness:
            query["freshness"] = request.freshness

        payload = self._get("/web/search", query)

        results = []
        web_data = payload.get("web", {})
        raw_results = web_data.get("results", []) if isinstance(web_data, dict) else []
        for item in raw_results:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
                "page_age": item.get("page_age", ""),
                "language": item.get("language", ""),
            })

        total_count = 0
        if isinstance(web_data, dict):
            total_count = int(web_data.get("totalEstimatedMatches", 0))

        return self._parse_message(
            {"results": results, "total_count": total_count},
            pb.WebSearchResponse,
        )

    def NewsSearch(
        self, request: pb.NewsSearchRequest, context: Any = None
    ) -> pb.NewsSearchResponse:
        query: dict[str, Any] = {"q": request.query}
        if request.count:
            query["count"] = request.count
        if request.country:
            query["country"] = request.country
        if request.freshness:
            query["freshness"] = request.freshness

        payload = self._get("/news/search", query)

        results = []
        news_data = payload.get("results", [])
        if not isinstance(news_data, list):
            news_data = []
        for item in news_data:
            source = item.get("meta_url", {})
            source_name = source.get("hostname", "") if isinstance(source, dict) else ""
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
                "age": item.get("age", ""),
                "source": source_name,
            })

        return self._parse_message({"results": results}, pb.NewsSearchResponse)

    def ImageSearch(
        self, request: pb.ImageSearchRequest, context: Any = None
    ) -> pb.ImageSearchResponse:
        query: dict[str, Any] = {"q": request.query}
        if request.count:
            query["count"] = request.count
        if request.country:
            query["country"] = request.country

        payload = self._get("/images/search", query)

        results = []
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raw_results = []
        for item in raw_results:
            props = item.get("properties", {})
            thumb = item.get("thumbnail", {})
            results.append({
                "title": item.get("title", ""),
                "url": props.get("url", "") if isinstance(props, dict) else "",
                "source_url": item.get("url", ""),
                "width": int(props.get("width", 0)) if isinstance(props, dict) else 0,
                "height": int(props.get("height", 0)) if isinstance(props, dict) else 0,
                "thumbnail_url": thumb.get("src", "") if isinstance(thumb, dict) else "",
            })

        return self._parse_message({"results": results}, pb.ImageSearchResponse)

    # -------------------------
    # HTTP helpers
    # -------------------------

    def _get(self, path: str, query: dict[str, Any] | None = None) -> Any:
        url = self._build_url(path, query)
        response = self._client.request("GET", url)

        try:
            payload = response.json() if response.content else {}
        except Exception as exc:
            raise RuntimeError(f"GET {url}: invalid JSON response: {exc}") from exc

        if response.status_code >= 400:
            raise RuntimeError(f"GET {url}: HTTP {response.status_code}: {payload}")

        return payload

    def _build_url(self, path: str, query: dict[str, Any] | None = None) -> str:
        full = f"{self._base_url}{path}"
        if not query:
            return full
        qs = urllib.parse.urlencode(
            [(k, self._to_http_scalar(v)) for k, v in query.items() if v is not None]
        )
        return f"{full}?{qs}" if qs else full

    def _to_http_scalar(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            return value
        if isinstance(value, int | float):
            return str(value)
        return str(value)

    # -------------------------
    # Generic helpers
    # -------------------------

    def _parse_message(self, payload: dict[str, Any], message_cls: type):
        message = message_cls()
        json_format.ParseDict(payload, message, ignore_unknown_fields=True)
        return message
