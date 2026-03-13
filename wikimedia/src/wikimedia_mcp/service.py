"""Wikimedia pageviews service implementation for Invariant Protocol."""

from __future__ import annotations

from typing import Any

import httpx
from google.protobuf import json_format

from wikimedia_mcp.gen.wikimedia.v1 import wikimedia_pb2 as pb

DEFAULT_BASE_URL = "https://wikimedia.org/api/rest_v1"

USER_AGENT = "invariant-mcp/1.0 (https://github.com/jim-technologies)"


class WikimediaService:
    """Implements WikimediaService -- Wikimedia pageview endpoints (no auth required)."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 15.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        )

    # -------------------------
    # RPC handlers
    # -------------------------

    def GetPageviews(
        self, request: pb.GetPageviewsRequest, context: Any = None
    ) -> pb.GetPageviewsResponse:
        path = (
            f"/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents"
            f"/{request.article}/daily/{request.start}/{request.end}"
        )
        payload = self._get(path)
        items = payload.get("items", [])
        return self._parse_message({"items": items}, pb.GetPageviewsResponse)

    def GetTopPages(
        self, request: pb.GetTopPagesRequest, context: Any = None
    ) -> pb.GetTopPagesResponse:
        path = (
            f"/metrics/pageviews/top/en.wikipedia/all-access"
            f"/{request.year}/{request.month}/{request.day}"
        )
        payload = self._get(path)
        articles = self._extract_top_articles(payload)
        return self._parse_message({"articles": articles}, pb.GetTopPagesResponse)

    def GetAggregatePageviews(
        self, request: pb.GetAggregatePageviewsRequest, context: Any = None
    ) -> pb.GetAggregatePageviewsResponse:
        path = (
            f"/metrics/pageviews/aggregate/en.wikipedia/all-access/all-agents"
            f"/daily/{request.start}/{request.end}"
        )
        payload = self._get(path)
        items = payload.get("items", [])
        return self._parse_message({"items": items}, pb.GetAggregatePageviewsResponse)

    def GetMostViewed(
        self, request: pb.GetMostViewedRequest, context: Any = None
    ) -> pb.GetMostViewedResponse:
        path = (
            f"/metrics/pageviews/top/en.wikipedia/all-access"
            f"/{request.year}/{request.month}/all-days"
        )
        payload = self._get(path)
        articles = self._extract_top_articles(payload)
        return self._parse_message({"articles": articles}, pb.GetMostViewedResponse)

    def GetUniqueDevices(
        self, request: pb.GetUniqueDevicesRequest, context: Any = None
    ) -> pb.GetUniqueDevicesResponse:
        path = (
            f"/metrics/unique-devices/en.wikipedia/all-sites"
            f"/daily/{request.start}/{request.end}"
        )
        payload = self._get(path)
        items = payload.get("items", [])
        return self._parse_message({"items": items}, pb.GetUniqueDevicesResponse)

    # -------------------------
    # Response transforms
    # -------------------------

    def _extract_top_articles(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract articles from the nested Wikimedia top-pages response."""
        items = payload.get("items", [])
        if not items:
            return []
        # The API nests articles inside items[0]["articles"]
        first = items[0] if isinstance(items, list) and len(items) > 0 else {}
        articles_raw = first.get("articles", [])
        result = []
        for a in articles_raw:
            result.append({
                "article": a.get("article", ""),
                "views": a.get("views", 0),
                "rank": a.get("rank", 0),
            })
        return result

    # -------------------------
    # HTTP helpers
    # -------------------------

    def _get(self, path: str) -> Any:
        url = f"{self._base_url}{path}"
        response = self._client.request(
            "GET",
            url,
            headers={"Accept": "application/json"},
        )

        try:
            payload = response.json() if response.content else {}
        except Exception as exc:
            raise RuntimeError(f"GET {url}: invalid JSON response: {exc}") from exc

        if response.status_code >= 400:
            raise RuntimeError(f"GET {url}: HTTP {response.status_code}: {payload}")

        return payload

    # -------------------------
    # Generic helpers
    # -------------------------

    def _parse_message(self, payload: dict[str, Any], message_cls: type):
        message = message_cls()
        json_format.ParseDict(payload, message, ignore_unknown_fields=True)
        return message
