"""Gate.io public market data service implementation for Invariant Protocol."""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from gateio_mcp.gen.gateio.v1 import gateio_pb2 as pb

DEFAULT_BASE_URL = "https://api.gateio.ws"


class GateioService:
    """Implements GateioService -- public market data endpoints (no auth required)."""

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

    def ListSpotTickers(
        self, request: pb.ListSpotTickersRequest, context: Any = None
    ) -> pb.ListSpotTickersResponse:
        query: dict[str, Any] = {}
        if self._has_field(request, "currency_pair"):
            query["currency_pair"] = request.currency_pair

        payload = self._get("/api/v4/spot/tickers", query)
        tickers = self._transform_spot_tickers(payload if isinstance(payload, list) else [])
        return self._parse_message({"tickers": tickers}, pb.ListSpotTickersResponse)

    def GetSpotOrderbook(
        self, request: pb.GetSpotOrderbookRequest, context: Any = None
    ) -> pb.GetSpotOrderbookResponse:
        query: dict[str, Any] = {"currency_pair": request.currency_pair}
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        payload = self._get("/api/v4/spot/order_book", query)
        result = self._transform_spot_orderbook(payload if isinstance(payload, dict) else {})
        return self._parse_message(result, pb.GetSpotOrderbookResponse)

    def GetSpotCandlesticks(
        self, request: pb.GetSpotCandlesticksRequest, context: Any = None
    ) -> pb.GetSpotCandlesticksResponse:
        query: dict[str, Any] = {"currency_pair": request.currency_pair}
        if self._has_field(request, "interval"):
            query["interval"] = request.interval
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        payload = self._get("/api/v4/spot/candlesticks", query)
        candlesticks = self._transform_candlesticks(payload if isinstance(payload, list) else [])
        return self._parse_message({"candlesticks": candlesticks}, pb.GetSpotCandlesticksResponse)

    def ListCurrencyPairs(
        self, request: pb.ListCurrencyPairsRequest, context: Any = None
    ) -> pb.ListCurrencyPairsResponse:
        payload = self._get("/api/v4/spot/currency_pairs")
        pairs = self._transform_currency_pairs(payload if isinstance(payload, list) else [])
        return self._parse_message({"currency_pairs": pairs}, pb.ListCurrencyPairsResponse)

    def ListFuturesTickers(
        self, request: pb.ListFuturesTickersRequest, context: Any = None
    ) -> pb.ListFuturesTickersResponse:
        query: dict[str, Any] = {}
        if self._has_field(request, "contract"):
            query["contract"] = request.contract

        payload = self._get("/api/v4/futures/usdt/tickers", query)
        tickers = self._transform_futures_tickers(payload if isinstance(payload, list) else [])
        return self._parse_message({"tickers": tickers}, pb.ListFuturesTickersResponse)

    def GetFuturesOrderbook(
        self, request: pb.GetFuturesOrderbookRequest, context: Any = None
    ) -> pb.GetFuturesOrderbookResponse:
        query: dict[str, Any] = {"contract": request.contract}
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        payload = self._get("/api/v4/futures/usdt/order_book", query)
        result = self._transform_futures_orderbook(payload if isinstance(payload, dict) else {})
        return self._parse_message(result, pb.GetFuturesOrderbookResponse)

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
    # Response transforms
    # -------------------------

    def _transform_spot_tickers(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform spot ticker entries -- Gate.io returns all values as strings."""
        result = []
        for item in items:
            result.append({
                "currency_pair": item.get("currency_pair", ""),
                "last": self._to_float(item.get("last")),
                "lowest_ask": self._to_float(item.get("lowest_ask")),
                "highest_bid": self._to_float(item.get("highest_bid")),
                "change_percentage": self._to_float(item.get("change_percentage")),
                "base_volume": self._to_float(item.get("base_volume")),
                "quote_volume": self._to_float(item.get("quote_volume")),
                "high_24h": self._to_float(item.get("high_24h")),
                "low_24h": self._to_float(item.get("low_24h")),
            })
        return result

    def _transform_spot_orderbook(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform spot orderbook: bids/asks are [[price_str, amount_str], ...]."""
        asks = []
        for row in data.get("asks", []):
            if isinstance(row, list) and len(row) >= 2:
                asks.append({"price": self._to_float(row[0]), "amount": self._to_float(row[1])})
        bids = []
        for row in data.get("bids", []):
            if isinstance(row, list) and len(row) >= 2:
                bids.append({"price": self._to_float(row[0]), "amount": self._to_float(row[1])})
        return {
            "current": int(data.get("current", 0)),
            "update": int(data.get("update", 0)),
            "asks": asks,
            "bids": bids,
        }

    def _transform_candlesticks(self, items: list) -> list[dict[str, Any]]:
        """Transform candlestick arrays: [timestamp, quote_vol, close, high, low, open, base_vol, is_closed]."""
        result = []
        for row in items:
            if isinstance(row, list) and len(row) >= 7:
                result.append({
                    "timestamp": int(row[0]),
                    "open": self._to_float(row[5]),
                    "high": self._to_float(row[3]),
                    "low": self._to_float(row[4]),
                    "close": self._to_float(row[2]),
                    "base_volume": self._to_float(row[6]),
                    "quote_volume": self._to_float(row[1]),
                    "is_closed": row[7] == "true" if len(row) > 7 else False,
                })
        return result

    def _transform_currency_pairs(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform currency pair entries."""
        result = []
        for item in items:
            result.append({
                "id": item.get("id", ""),
                "base": item.get("base", ""),
                "quote": item.get("quote", ""),
                "fee": self._to_float(item.get("fee")),
                "min_base_amount": self._to_float(item.get("min_base_amount")),
                "min_quote_amount": self._to_float(item.get("min_quote_amount")),
                "amount_precision": int(item.get("amount_precision", 0)),
                "precision": int(item.get("precision", 0)),
                "trade_status": item.get("trade_status", ""),
            })
        return result

    def _transform_futures_tickers(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform futures ticker entries -- Gate.io returns all values as strings."""
        result = []
        for item in items:
            result.append({
                "contract": item.get("contract", ""),
                "last": self._to_float(item.get("last")),
                "change_percentage": self._to_float(item.get("change_percentage")),
                "volume_24h": self._to_float(item.get("volume_24h")),
                "volume_24h_base": self._to_float(item.get("volume_24h_base")),
                "volume_24h_quote": self._to_float(item.get("volume_24h_quote")),
                "mark_price": self._to_float(item.get("mark_price")),
                "index_price": self._to_float(item.get("index_price")),
                "funding_rate": self._to_float(item.get("funding_rate")),
                "funding_rate_indicative": self._to_float(item.get("funding_rate_indicative")),
                "highest_bid": self._to_float(item.get("highest_bid")),
                "lowest_ask": self._to_float(item.get("lowest_ask")),
                "high_24h": self._to_float(item.get("high_24h")),
                "low_24h": self._to_float(item.get("low_24h")),
                "total_size": self._to_float(item.get("total_size")),
            })
        return result

    def _transform_futures_orderbook(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform futures orderbook: bids/asks are [{"p": price_str, "s": size}, ...]."""
        asks = []
        for entry in data.get("asks", []):
            if isinstance(entry, dict):
                asks.append({
                    "price": self._to_float(entry.get("p")),
                    "size": self._to_float(entry.get("s")),
                })
        bids = []
        for entry in data.get("bids", []):
            if isinstance(entry, dict):
                bids.append({
                    "price": self._to_float(entry.get("p")),
                    "size": self._to_float(entry.get("s")),
                })
        return {
            "current": int(data.get("current", 0)),
            "update": int(data.get("update", 0)),
            "asks": asks,
            "bids": bids,
        }

    # -------------------------
    # Generic helpers
    # -------------------------

    def _to_float(self, value: Any) -> float:
        """Safely convert a string or numeric value to float."""
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
