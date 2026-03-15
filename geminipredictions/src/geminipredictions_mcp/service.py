"""Gemini Predictions market data service implementation for Invariant Protocol."""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from geminipredictions_mcp.gen.geminipredictions.v1 import geminipredictions_pb2 as pb

DEFAULT_BASE_URL = "https://api.gemini.com"


class GeminiPredictionsService:
    """Implements GeminiPredictionsService -- Gemini prediction markets public endpoints."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str = "",
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
        if self._has_field(request, "status"):
            query["status"] = request.status
        if self._has_field(request, "category"):
            query["category"] = request.category

        payload = self._get("/v1/prediction-markets/events", query)
        raw_events = self._extract_events(payload)
        events = [self._transform_event(e) for e in raw_events]
        return self._parse_message({"events": events}, pb.ListEventsResponse)

    def GetEvent(
        self, request: pb.GetEventRequest, context: Any = None
    ) -> pb.GetEventResponse:
        ticker = request.event_ticker
        if not ticker:
            raise ValueError("event_ticker is required")

        path = f"/v1/prediction-markets/events/{urllib.parse.quote(ticker, safe='')}"
        payload = self._get(path)

        # The single-event endpoint may return the event directly or wrapped.
        event_data = payload
        if isinstance(payload.get("data"), dict):
            event_data = payload["data"]
        elif isinstance(payload.get("data"), list) and len(payload["data"]) == 1:
            event_data = payload["data"][0]

        event = self._transform_event(event_data)
        return self._parse_message({"event": event}, pb.GetEventResponse)

    def ListNewlyListedEvents(
        self, request: pb.ListNewlyListedEventsRequest, context: Any = None
    ) -> pb.ListNewlyListedEventsResponse:
        payload = self._get("/v1/prediction-markets/events/newly-listed")
        raw_events = self._extract_events(payload)
        events = [self._transform_event(e) for e in raw_events]
        return self._parse_message({"events": events}, pb.ListNewlyListedEventsResponse)

    def ListRecentlySettledEvents(
        self, request: pb.ListRecentlySettledEventsRequest, context: Any = None
    ) -> pb.ListRecentlySettledEventsResponse:
        payload = self._get("/v1/prediction-markets/events/recently-settled")
        raw_events = self._extract_events(payload)
        events = [self._transform_event(e) for e in raw_events]
        return self._parse_message(
            {"events": events}, pb.ListRecentlySettledEventsResponse
        )

    def ListUpcomingEvents(
        self, request: pb.ListUpcomingEventsRequest, context: Any = None
    ) -> pb.ListUpcomingEventsResponse:
        payload = self._get("/v1/prediction-markets/events/upcoming")
        raw_events = self._extract_events(payload)
        events = [self._transform_event(e) for e in raw_events]
        return self._parse_message({"events": events}, pb.ListUpcomingEventsResponse)

    def ListCategories(
        self, request: pb.ListCategoriesRequest, context: Any = None
    ) -> pb.ListCategoriesResponse:
        payload = self._get("/v1/prediction-markets/categories")
        categories = []
        if isinstance(payload, dict):
            raw = payload.get("categories", [])
            if isinstance(raw, list):
                categories = [str(c) for c in raw if isinstance(c, str)]
        return self._parse_message({"categories": categories}, pb.ListCategoriesResponse)

    # -------------------------
    # Data extraction / transforms
    # -------------------------

    def _extract_events(self, payload: Any) -> list[dict[str, Any]]:
        """Extract the 'data' array from an API response envelope."""
        if not isinstance(payload, dict):
            return []
        data = payload.get("data", [])
        if isinstance(data, list):
            return [e for e in data if isinstance(e, dict)]
        if isinstance(data, dict):
            return [data]
        return []

    def _transform_event(self, e: dict[str, Any]) -> dict[str, Any]:
        """Normalize a prediction event into proto-compatible fields."""
        contracts = []
        for c in e.get("contracts", []) or []:
            if isinstance(c, dict):
                contracts.append(self._transform_contract(c))

        tags = []
        for t in e.get("tags", []) or []:
            if isinstance(t, str):
                tags.append(t)

        subcategory = None
        raw_sub = e.get("subcategory")
        if isinstance(raw_sub, dict):
            subcategory = {
                "id": int(raw_sub.get("id", 0)),
                "slug": raw_sub.get("slug", ""),
                "name": raw_sub.get("name", ""),
            }

        result: dict[str, Any] = {
            "id": str(e.get("id", "")),
            "title": e.get("title", ""),
            "slug": e.get("slug", ""),
            "description": str(e.get("description", "")),
            "image_url": e.get("imageUrl", ""),
            "type": e.get("type", ""),
            "category": e.get("category", ""),
            "series": e.get("series", "") or "",
            "ticker": e.get("ticker", ""),
            "status": e.get("status", ""),
            "resolved_at": e.get("resolvedAt", "") or "",
            "created_at": e.get("createdAt", ""),
            "contracts": contracts,
            "volume": str(e.get("volume", "") or ""),
            "volume_24h": str(e.get("volume24h", "") or ""),
            "tags": tags,
            "expiry_date": e.get("expiryDate", "") or "",
            "effective_date": e.get("effectiveDate", "") or "",
            "is_live": bool(e.get("isLive", False)),
            "template": e.get("template", "") or "",
        }

        if subcategory is not None:
            result["subcategory"] = subcategory

        return result

    def _transform_contract(self, c: dict[str, Any]) -> dict[str, Any]:
        """Normalize a contract object into proto-compatible fields."""
        prices: dict[str, Any] = {}
        raw_prices = c.get("prices")
        if isinstance(raw_prices, dict):
            prices = {
                "best_bid": raw_prices.get("bestBid", ""),
                "best_ask": raw_prices.get("bestAsk", ""),
                "last_trade_price": raw_prices.get("lastTradePrice", ""),
            }

        return {
            "id": str(c.get("id", "")),
            "label": c.get("label", ""),
            "abbreviated_name": c.get("abbreviatedName", ""),
            "ticker": c.get("ticker", ""),
            "instrument_symbol": c.get("instrumentSymbol", ""),
            "status": c.get("status", ""),
            "market_state": c.get("marketState", ""),
            "prices": prices,
            "color": c.get("color", ""),
            "image_url": c.get("imageUrl", ""),
            "expiry_date": c.get("expiryDate", "") or "",
            "effective_date": c.get("effectiveDate", "") or "",
            "created_at": c.get("createdAt", "") or "",
            "resolved_at": c.get("resolvedAt", "") or "",
            "resolution_side": c.get("resolutionSide", "") or "",
            "sort_order": int(c.get("sortOrder", 0) or 0),
        }

    # -------------------------
    # HTTP helpers
    # -------------------------

    def _get(self, path: str, query: dict[str, Any] | None = None) -> Any:
        url = self._build_url(path, query)
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["X-GEMINI-APIKEY"] = self._api_key

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
