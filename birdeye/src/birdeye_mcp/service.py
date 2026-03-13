"""Birdeye Solana DEX data service implementation for Invariant Protocol."""

from __future__ import annotations

import os
import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from birdeye_mcp.gen.birdeye.v1 import birdeye_pb2 as pb

DEFAULT_BASE_URL = "https://public-api.birdeye.so"


class BirdeyeService:
    """Implements BirdeyeService -- Solana DEX data endpoints via Birdeye API."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        timeout: float = 15.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key or os.getenv("BIRDEYE_API_KEY", "")
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    # -------------------------
    # RPC handlers
    # -------------------------

    def GetTokenPrice(
        self, request: pb.GetTokenPriceRequest, context: Any = None
    ) -> pb.GetTokenPriceResponse:
        query: dict[str, Any] = {"address": request.address}
        payload = self._get("/defi/price", query)
        data = self._extract_data(payload)
        transformed = self._transform_token_price(data)
        return self._parse_message(transformed, pb.GetTokenPriceResponse)

    def GetMultiPrice(
        self, request: pb.GetMultiPriceRequest, context: Any = None
    ) -> pb.GetMultiPriceResponse:
        query: dict[str, Any] = {"list_address": request.list_address}
        payload = self._get("/defi/multi_price", query)
        data = self._extract_data(payload)
        # data is a dict of {address: {value, updateUnixTime, ...}}
        prices: dict[str, dict[str, Any]] = {}
        if isinstance(data, dict):
            for addr, info in data.items():
                if isinstance(info, dict):
                    prices[addr] = self._transform_token_price(info)
        return self._parse_message({"prices": prices}, pb.GetMultiPriceResponse)

    def GetTokenOverview(
        self, request: pb.GetTokenOverviewRequest, context: Any = None
    ) -> pb.GetTokenOverviewResponse:
        query: dict[str, Any] = {"address": request.address}
        payload = self._get("/defi/token_overview", query)
        data = self._extract_data(payload)
        transformed = self._transform_token_overview(data)
        return self._parse_message(transformed, pb.GetTokenOverviewResponse)

    def ListTokens(
        self, request: pb.ListTokensRequest, context: Any = None
    ) -> pb.ListTokensResponse:
        query: dict[str, Any] = {}
        if self._has_field(request, "sort_by"):
            query["sort_by"] = request.sort_by
        if self._has_field(request, "sort_type"):
            query["sort_type"] = request.sort_type
        if self._has_field(request, "limit"):
            query["limit"] = request.limit
        if self._has_field(request, "offset"):
            query["offset"] = request.offset

        payload = self._get("/defi/tokenlist", query)
        data = self._extract_data(payload)
        tokens_raw = data.get("tokens", []) if isinstance(data, dict) else []
        tokens = [self._transform_token_list_item(t) for t in tokens_raw]
        return self._parse_message({"tokens": tokens}, pb.ListTokensResponse)

    def GetOHLCV(
        self, request: pb.GetOHLCVRequest, context: Any = None
    ) -> pb.GetOHLCVResponse:
        query: dict[str, Any] = {
            "address": request.address,
            "type": request.type,
            "time_from": request.time_from,
            "time_to": request.time_to,
        }
        payload = self._get("/defi/ohlcv", query)
        data = self._extract_data(payload)
        items_raw = data.get("items", []) if isinstance(data, dict) else []
        if isinstance(data, list):
            items_raw = data
        items = [self._transform_ohlcv_item(item) for item in items_raw]
        return self._parse_message({"items": items}, pb.GetOHLCVResponse)

    def GetTradesToken(
        self, request: pb.GetTradesTokenRequest, context: Any = None
    ) -> pb.GetTradesTokenResponse:
        query: dict[str, Any] = {"address": request.address}
        if self._has_field(request, "limit"):
            query["limit"] = request.limit
        if self._has_field(request, "offset"):
            query["offset"] = request.offset

        payload = self._get("/defi/txs/token", query)
        data = self._extract_data(payload)
        items_raw = data.get("items", []) if isinstance(data, dict) else []
        if isinstance(data, list):
            items_raw = data
        items = [self._transform_trade_item(item) for item in items_raw]
        return self._parse_message({"items": items}, pb.GetTradesTokenResponse)

    def SearchToken(
        self, request: pb.SearchTokenRequest, context: Any = None
    ) -> pb.SearchTokenResponse:
        query: dict[str, Any] = {
            "keyword": request.keyword,
            "chain": "solana",
        }
        payload = self._get("/defi/v3/search", query)
        data = self._extract_data(payload)
        # v3/search returns items list of token results
        items_raw = data.get("items", []) if isinstance(data, dict) else []
        if isinstance(data, list):
            items_raw = data
        tokens = [self._transform_search_item(item) for item in items_raw]
        return self._parse_message({"tokens": tokens}, pb.SearchTokenResponse)

    # -------------------------
    # Data extraction
    # -------------------------

    def _extract_data(self, payload: Any) -> Any:
        """Unwrap Birdeye's ``{"success":true,"data":...}`` envelope."""
        if isinstance(payload, dict):
            return payload.get("data", payload)
        return payload

    # -------------------------
    # HTTP helpers
    # -------------------------

    def _get(self, path: str, query: dict[str, Any] | None = None) -> Any:
        url = self._build_url(path, query)
        headers: dict[str, str] = {
            "Accept": "application/json",
            "x-chain": "solana",
        }
        if self._api_key:
            headers["X-API-KEY"] = self._api_key

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
    # Response transforms
    # -------------------------

    def _transform_token_price(self, data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict):
            return {}
        return {
            "value": data.get("value", 0.0),
            "update_unix_time": data.get("updateUnixTime", 0.0),
            "update_human_time": str(data.get("updateHumanTime", "")),
        }

    def _transform_token_overview(self, data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict):
            return {}
        return {
            "address": data.get("address", ""),
            "symbol": data.get("symbol", ""),
            "name": data.get("name", ""),
            "decimals": data.get("decimals", 0),
            "price": data.get("price", 0.0),
            "liquidity": data.get("liquidity", 0.0),
            "v24h_usd": data.get("v24hUSD", 0.0),
            "v24h_change_percent": data.get("v24hChangePercent", 0.0),
            "mc": data.get("mc", 0.0),
            "price_change_24h_percent": data.get("priceChange24hPercent", 0.0),
            "trade_24h": data.get("trade24h", 0),
            "sell_24h": data.get("sell24h", 0),
            "buy_24h": data.get("buy24h", 0),
            "holder": data.get("holder", 0.0),
            "logo_uri": data.get("logoURI", ""),
            "last_trade_unix_time": data.get("lastTradeUnixTime", 0),
        }

    def _transform_token_list_item(self, item: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(item, dict):
            return {}
        return {
            "address": item.get("address", ""),
            "symbol": item.get("symbol", ""),
            "name": item.get("name", ""),
            "decimals": item.get("decimals", 0),
            "price": item.get("price", 0.0),
            "liquidity": item.get("liquidity", 0.0),
            "v24h_usd": item.get("v24hUSD", 0.0),
            "mc": item.get("mc", 0.0),
            "v24h_change_percent": item.get("v24hChangePercent", 0.0),
            "logo_uri": item.get("logoURI", ""),
            "last_trade_unix_time": item.get("lastTradeUnixTime", 0),
        }

    def _transform_ohlcv_item(self, item: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(item, dict):
            return {}
        return {
            "o": item.get("o", 0.0),
            "h": item.get("h", 0.0),
            "l": item.get("l", 0.0),
            "c": item.get("c", 0.0),
            "v": item.get("v", 0.0),
            "unix_time": item.get("unixTime", 0),
            "type": item.get("type", ""),
            "address": item.get("address", ""),
        }

    def _transform_trade_item(self, item: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(item, dict):
            return {}
        return {
            "tx_hash": item.get("txHash", ""),
            "source": item.get("source", ""),
            "block_unix_time": item.get("blockUnixTime", 0),
            "side": item.get("side", ""),
            "token_address": item.get("tokenAddress", ""),
            "amount": item.get("amount", 0.0),
            "volume_usd": item.get("volumeUsd", 0.0),
            "price": item.get("price", 0.0),
        }

    def _transform_search_item(self, item: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(item, dict):
            return {}
        return {
            "address": item.get("address", ""),
            "symbol": item.get("symbol", ""),
            "name": item.get("name", ""),
            "price": item.get("price", 0.0),
            "liquidity": item.get("liquidity", 0.0),
            "v24h_usd": item.get("v24hUSD", 0.0),
            "logo_uri": item.get("logoURI", ""),
            "network": item.get("network", ""),
        }

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
