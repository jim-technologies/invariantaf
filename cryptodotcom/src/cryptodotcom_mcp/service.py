"""Crypto.com Exchange public market data service implementation for Invariant Protocol."""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from cryptodotcom_mcp.gen.cryptodotcom.v1 import cryptodotcom_pb2 as pb

DEFAULT_BASE_URL = "https://api.crypto.com/exchange/v1"


class CryptoDotComService:
    """Implements CryptoDotComService -- public exchange data endpoints (no auth required)."""

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

    def GetInstruments(
        self, request: pb.GetInstrumentsRequest, context: Any = None
    ) -> pb.GetInstrumentsResponse:
        raw = self._get("/public/get-instruments")
        items = raw if isinstance(raw, list) else []
        instruments = []
        for item in items:
            instruments.append({
                "instrument_name": item.get("instrument_name", ""),
                "quote_currency": item.get("quote_currency", ""),
                "base_currency": item.get("base_currency", ""),
                "price_decimals": str(item.get("price_decimals", "")),
                "quantity_decimals": str(item.get("quantity_decimals", "")),
                "margin_trading_enabled": bool(item.get("margin_trading_enabled", False)),
            })
        return self._parse_message({"data": instruments}, pb.GetInstrumentsResponse)

    def GetTickers(
        self, request: pb.GetTickersRequest, context: Any = None
    ) -> pb.GetTickersResponse:
        query: dict[str, Any] = {}
        if self._has_field(request, "instrument_name"):
            query["instrument_name"] = request.instrument_name

        raw = self._get("/public/get-tickers", query)
        items = raw if isinstance(raw, list) else []
        tickers = []
        for item in items:
            tickers.append({
                "instrument_name": item.get("i", ""),
                "high": str(item.get("h", "")),
                "low": str(item.get("l", "")),
                "latest_trade": str(item.get("a", "")),
                "volume": str(item.get("v", "")),
                "best_bid": str(item.get("b", "")),
                "best_ask": str(item.get("k", "")),
                "price_change": str(item.get("c", "")),
                "price_change_percent": str(item.get("cp", "")),
                "timestamp": int(item.get("t", 0)),
            })
        return self._parse_message({"data": tickers}, pb.GetTickersResponse)

    def GetOrderbook(
        self, request: pb.GetOrderbookRequest, context: Any = None
    ) -> pb.GetOrderbookResponse:
        query: dict[str, Any] = {"instrument_name": request.instrument_name}
        if self._has_field(request, "depth"):
            query["depth"] = request.depth

        raw = self._get("/public/get-book", query)
        items = raw if isinstance(raw, list) else []
        if not items:
            return self._parse_message(
                {"data": {"bids": [], "asks": [], "timestamp": 0}},
                pb.GetOrderbookResponse,
            )

        book = items[0] if isinstance(items[0], dict) else {}
        bids = self._parse_levels(book.get("bids", []))
        asks = self._parse_levels(book.get("asks", []))
        return self._parse_message(
            {"data": {"bids": bids, "asks": asks, "timestamp": int(book.get("t", 0))}},
            pb.GetOrderbookResponse,
        )

    def GetCandlestick(
        self, request: pb.GetCandlestickRequest, context: Any = None
    ) -> pb.GetCandlestickResponse:
        query: dict[str, Any] = {"instrument_name": request.instrument_name}
        if self._has_field(request, "timeframe"):
            query["timeframe"] = request.timeframe

        raw = self._get("/public/get-candlestick", query)
        items = raw if isinstance(raw, list) else []
        candles = []
        for item in items:
            candles.append({
                "timestamp": int(item.get("t", 0)),
                "open": str(item.get("o", "")),
                "high": str(item.get("h", "")),
                "low": str(item.get("l", "")),
                "close": str(item.get("c", "")),
                "volume": str(item.get("v", "")),
            })
        return self._parse_message({"data": candles}, pb.GetCandlestickResponse)

    def GetTrades(
        self, request: pb.GetTradesRequest, context: Any = None
    ) -> pb.GetTradesResponse:
        query: dict[str, Any] = {"instrument_name": request.instrument_name}

        raw = self._get("/public/get-trades", query)
        items = raw if isinstance(raw, list) else []
        trades = []
        for item in items:
            trades.append({
                "trade_id": str(item.get("d", "")),
                "instrument_name": item.get("i", ""),
                "side": item.get("s", ""),
                "price": str(item.get("p", "")),
                "quantity": str(item.get("q", "")),
                "timestamp": int(item.get("t", 0)),
            })
        return self._parse_message({"data": trades}, pb.GetTradesResponse)

    # -------------------------
    # Data extraction / transforms
    # -------------------------

    def _parse_levels(self, raw_levels: list) -> list[dict[str, Any]]:
        """Parse orderbook bid/ask levels from [price, qty, count] arrays."""
        levels = []
        for entry in raw_levels:
            if isinstance(entry, list) and len(entry) >= 3:
                levels.append({
                    "price": str(entry[0]),
                    "quantity": str(entry[1]),
                    "count": str(entry[2]),
                })
        return levels

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

        # Unwrap Crypto.com envelope: {"code":0,"result":{"data":[...]}}
        if isinstance(payload, dict):
            code = payload.get("code", -1)
            if code != 0:
                raise RuntimeError(f"GET {url}: API error code {code}: {payload}")
            result = payload.get("result", {})
            if isinstance(result, dict):
                return result.get("data", result)

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
