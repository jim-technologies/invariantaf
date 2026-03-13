"""CoinMarketCal crypto events calendar service implementation for Invariant Protocol."""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from coinmarketcal_mcp.gen.coinmarketcal.v1 import coinmarketcal_pb2 as pb

DEFAULT_BASE_URL = "https://developers.coinmarketcal.com/v1"


class CoinMarketCalService:
    """Implements CoinMarketCalService -- crypto events calendar endpoints."""

    def __init__(
        self,
        *,
        api_key: str = "",
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 15.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    # -------------------------
    # RPC handlers
    # -------------------------

    def ListEvents(
        self, request: pb.ListEventsRequest, context: Any = None
    ) -> pb.ListEventsResponse:
        query: dict[str, Any] = {}
        if self._has_field(request, "max"):
            query["max"] = request.max
        if self._has_field(request, "page"):
            query["page"] = request.page
        if self._has_field(request, "coins"):
            query["coins"] = request.coins
        if self._has_field(request, "categories"):
            query["categories"] = request.categories
        if self._has_field(request, "date_range_start"):
            query["dateRangeStart"] = request.date_range_start
        if self._has_field(request, "date_range_end"):
            query["dateRangeEnd"] = request.date_range_end
        if self._has_field(request, "sort_by"):
            query["sortBy"] = request.sort_by
        if self._has_field(request, "show_only"):
            query["showOnly"] = request.show_only

        payload = self._get("/events", query or None)
        return self._build_events_response(payload)

    def ListCategories(
        self, request: pb.ListCategoriesRequest, context: Any = None
    ) -> pb.ListCategoriesResponse:
        payload = self._get("/categories")
        categories = self._extract_body(payload)
        if isinstance(categories, list):
            return self._parse_message({"categories": categories}, pb.ListCategoriesResponse)
        return self._parse_message({"categories": []}, pb.ListCategoriesResponse)

    def ListCoins(
        self, request: pb.ListCoinsRequest, context: Any = None
    ) -> pb.ListCoinsResponse:
        payload = self._get("/coins")
        coins = self._extract_body(payload)
        if isinstance(coins, list):
            normalized = []
            for c in coins:
                normalized.append({
                    "id": str(c.get("id", "")),
                    "name": c.get("name", ""),
                    "symbol": c.get("symbol", ""),
                    "rank": c.get("rank", 0),
                })
            return self._parse_message({"coins": normalized}, pb.ListCoinsResponse)
        return self._parse_message({"coins": []}, pb.ListCoinsResponse)

    # -------------------------
    # Response building
    # -------------------------

    def _build_events_response(self, payload: Any) -> pb.ListEventsResponse:
        """Build ListEventsResponse from raw API payload."""
        body = self._extract_body(payload)
        events_raw: list = []
        total = 0
        page = 1

        if isinstance(body, dict):
            events_raw = body.get("body", body.get("events", []))
            if isinstance(events_raw, list):
                pass
            else:
                events_raw = []
            total = body.get("total", len(events_raw))
            page = body.get("page", 1)
        elif isinstance(body, list):
            events_raw = body
            total = len(body)

        events = []
        for raw in events_raw:
            events.append(self._normalize_event(raw))

        return self._parse_message(
            {"events": events, "total": total, "page": page},
            pb.ListEventsResponse,
        )

    def _normalize_event(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize a single event from the API into proto-compatible dict."""
        coins = []
        for c in raw.get("coins", []):
            coins.append({
                "id": str(c.get("id", "")),
                "name": c.get("name", c.get("fullName", "")),
                "symbol": c.get("symbol", ""),
                "rank": c.get("rank", 0),
            })

        categories = []
        for cat in raw.get("categories", []):
            categories.append({
                "id": cat.get("id", 0),
                "name": cat.get("name", ""),
            })

        return {
            "id": raw.get("id", 0),
            "title": raw.get("title", {}).get("en", "") if isinstance(raw.get("title"), dict) else str(raw.get("title", "")),
            "description": raw.get("description", {}).get("en", "") if isinstance(raw.get("description"), dict) else str(raw.get("description", "")),
            "source": raw.get("source", ""),
            "is_hot": raw.get("is_hot", raw.get("isHot", False)),
            "date_event": raw.get("date_event", ""),
            "created_date": raw.get("created_date", ""),
            "coins": coins,
            "categories": categories,
            "percentage": raw.get("percentage", 0),
            "positive_vote_count": raw.get("positive_vote_count", raw.get("positiveVoteCount", 0)),
            "vote_count": raw.get("vote_count", raw.get("voteCount", 0)),
        }

    # -------------------------
    # Result extraction
    # -------------------------

    def _extract_body(self, payload: Any) -> Any:
        """Unwrap the CoinMarketCal response envelope if present."""
        if isinstance(payload, dict) and "body" in payload:
            return payload["body"]
        return payload

    # -------------------------
    # HTTP helpers
    # -------------------------

    def _get(self, path: str, query: dict[str, Any] | None = None) -> Any:
        url = self._build_url(path, query)
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["x-api-key"] = self._api_key

        response = self._client.request("GET", url, headers=headers)

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

    def _has_field(self, message: Any, field_name: str) -> bool:
        try:
            return bool(message.HasField(field_name))
        except ValueError:
            return False
