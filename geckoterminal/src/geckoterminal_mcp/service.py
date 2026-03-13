"""GeckoTerminal DEX analytics service implementation for Invariant Protocol."""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from geckoterminal_mcp.gen.geckoterminal.v1 import geckoterminal_pb2 as pb

DEFAULT_BASE_URL = "https://api.geckoterminal.com"


class GeckoTerminalService:
    """Implements GeckoTerminalService -- public DEX analytics endpoints (no auth required)."""

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

    def ListNetworks(
        self, request: pb.ListNetworksRequest, context: Any = None
    ) -> pb.ListNetworksResponse:
        payload = self._get("/api/v2/networks")
        items = self._extract_list(payload)
        networks = [self._extract_attributes(item, keep_id=True) for item in items]
        return self._parse_message({"networks": networks}, pb.ListNetworksResponse)

    def GetTrendingPools(
        self, request: pb.GetTrendingPoolsRequest, context: Any = None
    ) -> pb.GetTrendingPoolsResponse:
        if self._has_field(request, "network") and request.network:
            path = f"/api/v2/networks/{request.network}/trending_pools"
        else:
            path = "/api/v2/networks/trending_pools"

        payload = self._get(path)
        items = self._extract_list(payload)
        pools = [self._transform_pool(item) for item in items]
        return self._parse_message({"pools": pools}, pb.GetTrendingPoolsResponse)

    def GetPool(
        self, request: pb.GetPoolRequest, context: Any = None
    ) -> pb.GetPoolResponse:
        path = f"/api/v2/networks/{request.network}/pools/{request.address}"
        payload = self._get(path)
        data = self._extract_data(payload)
        pool = self._transform_pool(data)
        return self._parse_message({"pool": pool}, pb.GetPoolResponse)

    def SearchPools(
        self, request: pb.SearchPoolsRequest, context: Any = None
    ) -> pb.SearchPoolsResponse:
        query: dict[str, Any] = {"query": request.query}
        if self._has_field(request, "network") and request.network:
            query["network"] = request.network

        payload = self._get("/api/v2/search/pools", query)
        items = self._extract_list(payload)
        pools = [self._transform_pool(item) for item in items]
        return self._parse_message({"pools": pools}, pb.SearchPoolsResponse)

    def GetPoolOHLCV(
        self, request: pb.GetPoolOHLCVRequest, context: Any = None
    ) -> pb.GetPoolOHLCVResponse:
        path = (
            f"/api/v2/networks/{request.network}/pools/"
            f"{request.pool_address}/ohlcv/{request.timeframe}"
        )
        query: dict[str, Any] = {}
        if self._has_field(request, "aggregate"):
            query["aggregate"] = request.aggregate
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        payload = self._get(path, query if query else None)
        data = self._extract_data(payload)
        attrs = data.get("attributes", data) if isinstance(data, dict) else {}
        ohlcv_list = attrs.get("ohlcv_list", []) if isinstance(attrs, dict) else []
        candles = []
        for row in ohlcv_list:
            if isinstance(row, list) and len(row) >= 6:
                candles.append({
                    "timestamp": int(row[0]),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                })
        return self._parse_message({"candles": candles}, pb.GetPoolOHLCVResponse)

    def GetNewPools(
        self, request: pb.GetNewPoolsRequest, context: Any = None
    ) -> pb.GetNewPoolsResponse:
        path = f"/api/v2/networks/{request.network}/new_pools"
        payload = self._get(path)
        items = self._extract_list(payload)
        pools = [self._transform_pool(item) for item in items]
        return self._parse_message({"pools": pools}, pb.GetNewPoolsResponse)

    def GetTopPools(
        self, request: pb.GetTopPoolsRequest, context: Any = None
    ) -> pb.GetTopPoolsResponse:
        path = f"/api/v2/networks/{request.network}/dexes/{request.dex}/pools"
        payload = self._get(path)
        items = self._extract_list(payload)
        pools = [self._transform_pool(item) for item in items]
        return self._parse_message({"pools": pools}, pb.GetTopPoolsResponse)

    # -------------------------
    # JSON:API unwrapping
    # -------------------------

    def _extract_data(self, payload: Any) -> Any:
        """Extract the ``data`` field from a JSON:API response."""
        if isinstance(payload, dict):
            return payload.get("data", payload)
        return payload

    def _extract_list(self, payload: Any) -> list:
        """Extract a list from a JSON:API response ``data`` field."""
        data = self._extract_data(payload)
        if isinstance(data, list):
            return data
        return []

    def _extract_attributes(self, item: Any, *, keep_id: bool = False) -> dict[str, Any]:
        """Extract attributes from a JSON:API resource object."""
        if not isinstance(item, dict):
            return {}
        attrs = dict(item.get("attributes", {}))
        if keep_id and "id" in item:
            attrs["id"] = item["id"]
        return attrs

    # -------------------------
    # Pool transform
    # -------------------------

    def _transform_pool(self, item: Any) -> dict[str, Any]:
        """Transform a JSON:API pool resource into a flat dict matching the proto Pool message."""
        if not isinstance(item, dict):
            return {}
        attrs = item.get("attributes", item)
        relationships = item.get("relationships", {})

        pool: dict[str, Any] = {
            "address": attrs.get("address", ""),
            "name": attrs.get("name", ""),
            "base_token_price_usd": self._to_float(attrs.get("base_token_price_usd")),
            "quote_token_price_usd": self._to_float(attrs.get("quote_token_price_usd")),
            "fdv_usd": self._to_float(attrs.get("fdv_usd")),
            "market_cap_usd": self._to_float(attrs.get("market_cap_usd")),
            "reserve_in_usd": self._to_float(attrs.get("reserve_in_usd")),
            "price_change_percentage_m5": self._to_float(
                attrs.get("price_change_percentage", {}).get("m5")
                if isinstance(attrs.get("price_change_percentage"), dict)
                else None
            ),
            "price_change_percentage_h1": self._to_float(
                attrs.get("price_change_percentage", {}).get("h1")
                if isinstance(attrs.get("price_change_percentage"), dict)
                else None
            ),
            "price_change_percentage_h24": self._to_float(
                attrs.get("price_change_percentage", {}).get("h24")
                if isinstance(attrs.get("price_change_percentage"), dict)
                else None
            ),
            "pool_created_at": attrs.get("pool_created_at", ""),
        }

        # Volume fields
        volume = attrs.get("volume_usd", {})
        if isinstance(volume, dict):
            pool["volume_usd_m5"] = self._to_float(volume.get("m5"))
            pool["volume_usd_h1"] = self._to_float(volume.get("h1"))
            pool["volume_usd_h24"] = self._to_float(volume.get("h24"))
        else:
            pool["volume_usd_h24"] = self._to_float(volume)

        # Extract network and dex from relationships or id
        pool["network_id"] = self._extract_relationship_id(relationships, "network")
        pool["dex_id"] = self._extract_relationship_id(relationships, "dex")

        # If network/dex not in relationships, try to parse from item id
        if not pool["network_id"] and "id" in item:
            parts = str(item["id"]).split("_", 1)
            if len(parts) >= 1:
                pool["network_id"] = parts[0]

        # Base and quote tokens
        base_token_data = self._extract_relationship_id(relationships, "base_token")
        quote_token_data = self._extract_relationship_id(relationships, "quote_token")

        # Try included data for token info or fall back to relationship id
        if base_token_data:
            pool["base_token"] = {"address": base_token_data}
        if quote_token_data:
            pool["quote_token"] = {"address": quote_token_data}

        return pool

    def _extract_relationship_id(self, relationships: dict, key: str) -> str:
        """Extract the id from a JSON:API relationship."""
        rel = relationships.get(key, {})
        if isinstance(rel, dict):
            data = rel.get("data", {})
            if isinstance(data, dict):
                return str(data.get("id", ""))
        return ""

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

    def _to_float(self, value: Any) -> float:
        """Safely convert a value to float, returning 0.0 on failure."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _parse_message(self, payload: dict[str, Any], message_cls: type):
        message = message_cls()
        json_format.ParseDict(payload, message, ignore_unknown_fields=True)
        return message

    def _has_field(self, message: Any, field_name: str) -> bool:
        try:
            return bool(message.HasField(field_name))
        except ValueError:
            return False
