"""Alternative.me public crypto data service implementation for Invariant Protocol."""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from alternativeme_mcp.gen.alternativeme.v1 import alternativeme_pb2 as pb

DEFAULT_BASE_URL = "https://api.alternative.me"


class AlternativeMeService:
    """Implements AlternativeMeService -- public crypto data endpoints (no auth required)."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 15.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    # -------------------------
    # RPC handlers
    # -------------------------

    def GetFearGreedIndex(
        self, request: pb.GetFearGreedIndexRequest, context: Any = None
    ) -> pb.GetFearGreedIndexResponse:
        query: dict[str, Any] = {"format": "json"}
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        payload = self._get("/fng/", query)
        raw_data = payload.get("data", []) if isinstance(payload, dict) else []
        entries = []
        for item in raw_data:
            entries.append({
                "value": str(item.get("value", "")),
                "value_classification": item.get("value_classification", ""),
                "timestamp": int(item.get("timestamp", 0)),
                "time_until_update": str(item.get("time_until_update", "")),
            })
        return self._parse_message({"data": entries}, pb.GetFearGreedIndexResponse)

    def GetGlobalMarketData(
        self, request: pb.GetGlobalMarketDataRequest, context: Any = None
    ) -> pb.GetGlobalMarketDataResponse:
        query: dict[str, Any] = {"convert": "USD"}
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        payload = self._get("/v2/ticker/", query)
        raw_data = self._extract_ticker_data(payload)
        tickers = [self._transform_coin_ticker(item) for item in raw_data]
        return self._parse_message({"data": tickers}, pb.GetGlobalMarketDataResponse)

    def GetCoinData(
        self, request: pb.GetCoinDataRequest, context: Any = None
    ) -> pb.GetCoinDataResponse:
        query: dict[str, Any] = {"convert": "USD"}

        payload = self._get(f"/v2/ticker/{request.id}/", query)
        raw_data = payload.get("data", {}) if isinstance(payload, dict) else {}
        if isinstance(raw_data, dict) and not any(
            k in raw_data for k in ("name", "symbol", "id")
        ):
            # The API wraps single coin in {"data": {"<id>": {...}}}
            values = list(raw_data.values())
            if values and isinstance(values[0], dict):
                raw_data = values[0]
        ticker = self._transform_coin_ticker(raw_data)
        return self._parse_message({"data": ticker}, pb.GetCoinDataResponse)

    def GetListings(
        self, request: pb.GetListingsRequest, context: Any = None
    ) -> pb.GetListingsResponse:
        query: dict[str, Any] = {"convert": "USD"}
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        payload = self._get("/v2/listings/", query)
        raw_data = payload.get("data", []) if isinstance(payload, dict) else []
        listings = []
        for item in raw_data:
            listings.append({
                "id": str(item.get("id", "")),
                "name": item.get("name", ""),
                "symbol": item.get("symbol", ""),
                "website_slug": item.get("website_slug", ""),
                "rank": int(item.get("rank", 0)),
            })
        return self._parse_message({"data": listings}, pb.GetListingsResponse)

    # -------------------------
    # Data extraction / transforms
    # -------------------------

    def _extract_ticker_data(self, payload: Any) -> list[dict[str, Any]]:
        """Extract ticker list from the v2/ticker response envelope.

        The API returns ``{"data": {"<id>": {...}, ...}}`` -- a dict keyed by id.
        """
        if not isinstance(payload, dict):
            return []
        data = payload.get("data", {})
        if isinstance(data, dict):
            return list(data.values())
        if isinstance(data, list):
            return data
        return []

    def _transform_coin_ticker(self, item: dict[str, Any]) -> dict[str, Any]:
        """Normalize a coin ticker entry into proto-compatible fields."""
        quotes = item.get("quotes", {})
        usd = quotes.get("USD", {}) if isinstance(quotes, dict) else {}
        return {
            "id": str(item.get("id", "")),
            "name": item.get("name", ""),
            "symbol": item.get("symbol", ""),
            "rank": int(item.get("rank", 0)),
            "price_usd": str(usd.get("price", "")),
            "price_btc": "",
            "market_cap_usd": str(usd.get("market_cap", "")),
            "volume_24h_usd": str(usd.get("volume_24h", "")),
            "percent_change_1h": str(usd.get("percentage_change_1h", usd.get("percent_change_1h", ""))),
            "percent_change_24h": str(usd.get("percentage_change_24h", usd.get("percent_change_24h", ""))),
            "percent_change_7d": str(usd.get("percentage_change_7d", usd.get("percent_change_7d", ""))),
            "last_updated": int(item.get("last_updated", 0)),
        }

    # -------------------------
    # HTTP helpers
    # -------------------------

    def _get(self, path: str, query: dict[str, Any] | None = None) -> Any:
        url = self._build_url(path, query)
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
