"""Bitget public market data service implementation for Invariant Protocol."""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from bitget_mcp.gen.bitget.v1 import bitget_pb2 as pb

DEFAULT_BASE_URL = "https://api.bitget.com"


class BitgetService:
    """Implements BitgetService -- public market data endpoints (no auth required)."""

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
        if self._has_field(request, "symbol"):
            query["symbol"] = request.symbol

        data = self._get("/api/v2/spot/market/tickers", query)
        tickers = data if isinstance(data, list) else []
        return self._parse_message({"tickers": tickers}, pb.ListSpotTickersResponse)

    def GetSpotOrderbook(
        self, request: pb.GetSpotOrderbookRequest, context: Any = None
    ) -> pb.GetSpotOrderbookResponse:
        query: dict[str, Any] = {"symbol": request.symbol}
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        data = self._get("/api/v2/spot/market/orderbook", query)
        self._transform_orderbook(data)
        return self._parse_message(data, pb.GetSpotOrderbookResponse)

    def GetSpotCandles(
        self, request: pb.GetSpotCandlesRequest, context: Any = None
    ) -> pb.GetSpotCandlesResponse:
        query: dict[str, Any] = {
            "symbol": request.symbol,
            "granularity": request.granularity,
        }
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        data = self._get("/api/v2/spot/market/candles", query)
        candles = self._transform_candles(data)
        return self._parse_message({"candles": candles}, pb.GetSpotCandlesResponse)

    def ListFuturesTickers(
        self, request: pb.ListFuturesTickersRequest, context: Any = None
    ) -> pb.ListFuturesTickersResponse:
        query: dict[str, Any] = {"productType": request.product_type}

        data = self._get("/api/v2/mix/market/tickers", query)
        tickers = data if isinstance(data, list) else []
        return self._parse_message({"tickers": tickers}, pb.ListFuturesTickersResponse)

    def GetFuturesOrderbook(
        self, request: pb.GetFuturesOrderbookRequest, context: Any = None
    ) -> pb.GetFuturesOrderbookResponse:
        query: dict[str, Any] = {
            "symbol": request.symbol,
            "productType": request.product_type,
        }
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        data = self._get("/api/v2/mix/market/merge-depth", query)
        self._transform_orderbook(data)
        return self._parse_message(data, pb.GetFuturesOrderbookResponse)

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

        # Bitget wraps responses in {"code":"00000","msg":"success","data":{...}}
        if isinstance(payload, dict) and "data" in payload:
            code = payload.get("code", "")
            if code != "00000":
                raise RuntimeError(
                    f"GET {url}: Bitget API error code={code} msg={payload.get('msg', '')}"
                )
            return payload["data"]

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

    def _transform_orderbook(self, data: dict[str, Any]) -> None:
        """Transform raw orderbook data: convert [["price", "amount"], ...] to dicts."""
        for side in ("asks", "bids"):
            levels = data.get(side, [])
            parsed: list[dict[str, str]] = []
            for row in levels:
                if isinstance(row, list) and len(row) >= 2:
                    parsed.append({"price": str(row[0]), "amount": str(row[1])})
            data[side] = parsed

    def _transform_candles(self, data: Any) -> list[dict[str, str]]:
        """Transform raw candle data: convert arrays to dicts.

        Bitget returns candles as arrays:
        [ts, open, high, low, close, baseVolume, quoteVolume, usdVolume]
        """
        candles: list[dict[str, str]] = []
        if not isinstance(data, list):
            return candles
        for row in data:
            if isinstance(row, list) and len(row) >= 8:
                candles.append({
                    "ts": str(row[0]),
                    "open": str(row[1]),
                    "high": str(row[2]),
                    "low": str(row[3]),
                    "close": str(row[4]),
                    "base_volume": str(row[5]),
                    "quote_volume": str(row[6]),
                    "usd_volume": str(row[7]),
                })
        return candles

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
