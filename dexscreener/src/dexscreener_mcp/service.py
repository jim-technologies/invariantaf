"""DexScreener public API service implementation for Invariant Protocol."""

from __future__ import annotations

from typing import Any

import httpx
from google.protobuf import json_format

from dexscreener_mcp.gen.dexscreener.v1 import dexscreener_pb2 as pb

DEFAULT_BASE_URL = "https://api.dexscreener.com"


def _snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    out: list[str] = []
    for ch in name:
        if ch.isupper():
            out.append("_")
            out.append(ch.lower())
        else:
            out.append(ch)
    return "".join(out).lstrip("_")


def _to_snake_keys(obj: Any) -> Any:
    """Recursively convert dict keys from camelCase to snake_case."""
    if isinstance(obj, dict):
        return {_snake(k): _to_snake_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_snake_keys(item) for item in obj]
    return obj


class DexScreenerService:
    """Implements DexScreenerService -- public API endpoints (no auth required)."""

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

    def SearchPairs(
        self, request: pb.SearchPairsRequest, context: Any = None
    ) -> pb.SearchPairsResponse:
        payload = self._get(f"/latest/dex/search?q={request.query}")
        pairs = self._extract_pairs(payload)
        return self._parse_message({"pairs": pairs}, pb.SearchPairsResponse)

    def GetPairsByChainAndAddress(
        self, request: pb.GetPairsByChainAndAddressRequest, context: Any = None
    ) -> pb.GetPairsByChainAndAddressResponse:
        payload = self._get(
            f"/latest/dex/pairs/{request.chain_id}/{request.pair_addresses}"
        )
        pairs = self._extract_pairs(payload)
        return self._parse_message(
            {"pairs": pairs}, pb.GetPairsByChainAndAddressResponse
        )

    def GetTokenPairs(
        self, request: pb.GetTokenPairsRequest, context: Any = None
    ) -> pb.GetTokenPairsResponse:
        payload = self._get(f"/latest/dex/tokens/{request.token_addresses}")
        pairs = self._extract_pairs(payload)
        return self._parse_message({"pairs": pairs}, pb.GetTokenPairsResponse)

    def GetLatestTokenProfiles(
        self, request: pb.GetLatestTokenProfilesRequest, context: Any = None
    ) -> pb.GetLatestTokenProfilesResponse:
        payload = self._get("/token-profiles/latest/v1")
        profiles = self._normalize_profiles(payload)
        return self._parse_message(
            {"profiles": profiles}, pb.GetLatestTokenProfilesResponse
        )

    def GetLatestBoostedTokens(
        self, request: pb.GetLatestBoostedTokensRequest, context: Any = None
    ) -> pb.GetLatestBoostedTokensResponse:
        payload = self._get("/token-boosts/latest/v1")
        tokens = self._normalize_boosted_tokens(payload)
        return self._parse_message(
            {"tokens": tokens}, pb.GetLatestBoostedTokensResponse
        )

    def GetTopBoostedTokens(
        self, request: pb.GetTopBoostedTokensRequest, context: Any = None
    ) -> pb.GetTopBoostedTokensResponse:
        payload = self._get("/token-boosts/top/v1")
        tokens = self._normalize_boosted_tokens(payload)
        return self._parse_message(
            {"tokens": tokens}, pb.GetTopBoostedTokensResponse
        )

    def GetOrdersByToken(
        self, request: pb.GetOrdersByTokenRequest, context: Any = None
    ) -> pb.GetOrdersByTokenResponse:
        payload = self._get(
            f"/orders/v1/{request.chain_id}/{request.token_address}"
        )
        return self._parse_orders(payload)

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
    # Response transforms
    # -------------------------

    def _extract_pairs(self, payload: Any) -> list[dict[str, Any]]:
        """Extract and normalize pairs from API response."""
        if isinstance(payload, dict):
            raw_pairs = payload.get("pairs", [])
        elif isinstance(payload, list):
            raw_pairs = payload
        else:
            raw_pairs = []
        if raw_pairs is None:
            raw_pairs = []
        return [self._normalize_pair(p) for p in raw_pairs]

    def _normalize_pair(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Convert a raw pair dict to snake_case and flatten for protobuf."""
        pair: dict[str, Any] = {
            "chain_id": raw.get("chainId", ""),
            "dex_id": raw.get("dexId", ""),
            "url": raw.get("url", ""),
            "pair_address": raw.get("pairAddress", ""),
            "price_native": raw.get("priceNative", ""),
            "price_usd": raw.get("priceUsd", ""),
            "fdv": raw.get("fdv", 0) or 0,
            "market_cap": raw.get("marketCap", 0) or 0,
            "pair_created_at": raw.get("pairCreatedAt", 0) or 0,
            "labels": raw.get("labels", []) or [],
        }

        base = raw.get("baseToken") or {}
        pair["base_token"] = {
            "address": base.get("address", ""),
            "name": base.get("name", ""),
            "symbol": base.get("symbol", ""),
        }

        quote = raw.get("quoteToken") or {}
        pair["quote_token"] = {
            "address": quote.get("address", ""),
            "name": quote.get("name", ""),
            "symbol": quote.get("symbol", ""),
        }

        txns_raw = raw.get("txns") or {}
        txns: dict[str, Any] = {}
        for period in ("m5", "h1", "h6", "h24"):
            t = txns_raw.get(period) or {}
            txns[period] = {
                "buys": t.get("buys", 0) or 0,
                "sells": t.get("sells", 0) or 0,
            }
        pair["txns"] = txns

        vol_raw = raw.get("volume") or {}
        pair["volume"] = {
            "m5": vol_raw.get("m5", 0) or 0,
            "h1": vol_raw.get("h1", 0) or 0,
            "h6": vol_raw.get("h6", 0) or 0,
            "h24": vol_raw.get("h24", 0) or 0,
        }

        pc_raw = raw.get("priceChange") or {}
        pair["price_change"] = {
            "m5": pc_raw.get("m5", 0) or 0,
            "h1": pc_raw.get("h1", 0) or 0,
            "h6": pc_raw.get("h6", 0) or 0,
            "h24": pc_raw.get("h24", 0) or 0,
        }

        liq_raw = raw.get("liquidity") or {}
        pair["liquidity"] = {
            "usd": liq_raw.get("usd", 0) or 0,
            "base": liq_raw.get("base", 0) or 0,
            "quote": liq_raw.get("quote", 0) or 0,
        }

        return pair

    def _normalize_profiles(self, payload: Any) -> list[dict[str, Any]]:
        """Normalize token profiles from API response."""
        raw_list = payload if isinstance(payload, list) else []
        profiles = []
        for raw in raw_list:
            profile: dict[str, Any] = {
                "url": raw.get("url", ""),
                "chain_id": raw.get("chainId", ""),
                "token_address": raw.get("tokenAddress", ""),
                "icon": raw.get("icon", ""),
                "header": raw.get("header", ""),
                "open_graph": raw.get("openGraph", ""),
                "description": raw.get("description", ""),
            }
            links_raw = raw.get("links") or []
            profile["links"] = [
                {
                    "label": lnk.get("label", ""),
                    "type": lnk.get("type", ""),
                    "url": lnk.get("url", ""),
                }
                for lnk in links_raw
            ]
            profiles.append(profile)
        return profiles

    def _normalize_boosted_tokens(self, payload: Any) -> list[dict[str, Any]]:
        """Normalize boosted tokens from API response."""
        raw_list = payload if isinstance(payload, list) else []
        tokens = []
        for raw in raw_list:
            token: dict[str, Any] = {
                "url": raw.get("url", ""),
                "chain_id": raw.get("chainId", ""),
                "token_address": raw.get("tokenAddress", ""),
                "description": raw.get("description", ""),
                "icon": raw.get("icon", ""),
                "header": raw.get("header", ""),
                "open_graph": raw.get("openGraph", ""),
                "total_amount": raw.get("totalAmount", 0) or 0,
                "amount": raw.get("amount", 0) or 0,
            }
            links_raw = raw.get("links") or []
            token["links"] = [
                {
                    "label": lnk.get("label", ""),
                    "type": lnk.get("type", ""),
                    "url": lnk.get("url", ""),
                }
                for lnk in links_raw
            ]
            tokens.append(token)
        return tokens

    def _parse_orders(self, payload: Any) -> pb.GetOrdersByTokenResponse:
        """Parse orders/boosts response which can be a list or a dict."""
        orders: list[dict[str, Any]] = []
        boosts: list[dict[str, Any]] = []

        if isinstance(payload, list):
            # The API may return a flat list of order objects
            for item in payload:
                item_type = item.get("type", "")
                normalized = {
                    "chain_id": item.get("chainId", ""),
                    "token_address": item.get("tokenAddress", ""),
                    "type": item_type,
                    "status": item.get("status", ""),
                    "payment_timestamp": item.get("paymentTimestamp", 0) or 0,
                }
                orders.append(normalized)
        elif isinstance(payload, dict):
            for item in payload.get("orders", []):
                orders.append({
                    "chain_id": item.get("chainId", ""),
                    "token_address": item.get("tokenAddress", ""),
                    "type": item.get("type", ""),
                    "status": item.get("status", ""),
                    "payment_timestamp": item.get("paymentTimestamp", 0) or 0,
                })
            for item in payload.get("boosts", []):
                boosts.append({
                    "chain_id": item.get("chainId", ""),
                    "token_address": item.get("tokenAddress", ""),
                    "id": item.get("id", ""),
                    "amount": item.get("amount", 0) or 0,
                    "payment_timestamp": item.get("paymentTimestamp", 0) or 0,
                })

        return self._parse_message(
            {"orders": orders, "boosts": boosts}, pb.GetOrdersByTokenResponse
        )

    # -------------------------
    # Generic helpers
    # -------------------------

    def _parse_message(self, payload: dict[str, Any], message_cls: type):
        message = message_cls()
        json_format.ParseDict(payload, message, ignore_unknown_fields=True)
        return message
