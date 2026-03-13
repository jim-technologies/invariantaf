"""KuCoin public market data service implementation for Invariant Protocol."""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from kucoin_mcp.gen.kucoin.v1 import kucoin_pb2 as pb

DEFAULT_BASE_URL = "https://api.kucoin.com"


class KucoinService:
    """Implements KucoinService -- public market data endpoints (no auth required)."""

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

    def GetAllTickers(
        self, request: pb.GetAllTickersRequest, context: Any = None
    ) -> pb.GetAllTickersResponse:
        payload = self._get("/api/v1/market/allTickers")
        # payload["data"] = {"time": ..., "ticker": [...]}
        time_val = payload.get("time", 0)
        tickers = payload.get("ticker", [])
        return self._parse_message(
            {"time": time_val, "ticker": tickers},
            pb.GetAllTickersResponse,
        )

    def GetTicker(
        self, request: pb.GetTickerRequest, context: Any = None
    ) -> pb.GetTickerResponse:
        query: dict[str, Any] = {"symbol": request.symbol}
        payload = self._get("/api/v1/market/stats", query)
        return self._parse_message(payload, pb.GetTickerResponse)

    def GetOrderbook(
        self, request: pb.GetOrderbookRequest, context: Any = None
    ) -> pb.GetOrderbookResponse:
        query: dict[str, Any] = {"symbol": request.symbol}
        payload = self._get("/api/v1/market/orderbook/level2_20", query)
        self._transform_orderbook(payload)
        return self._parse_message(payload, pb.GetOrderbookResponse)

    def GetKlines(
        self, request: pb.GetKlinesRequest, context: Any = None
    ) -> pb.GetKlinesResponse:
        query: dict[str, Any] = {
            "symbol": request.symbol,
            "type": request.type,
        }
        if request.start_at:
            query["startAt"] = request.start_at
        if request.end_at:
            query["endAt"] = request.end_at

        payload = self._get("/api/v1/market/candles", query)
        # payload is a list of lists: [[time, open, close, high, low, volume, turnover], ...]
        klines = []
        if isinstance(payload, list):
            for row in payload:
                if isinstance(row, list) and len(row) >= 7:
                    klines.append({
                        "time": str(row[0]),
                        "open": str(row[1]),
                        "close": str(row[2]),
                        "high": str(row[3]),
                        "low": str(row[4]),
                        "volume": str(row[5]),
                        "turnover": str(row[6]),
                    })
        return self._parse_message({"klines": klines}, pb.GetKlinesResponse)

    def ListSymbols(
        self, request: pb.ListSymbolsRequest, context: Any = None
    ) -> pb.ListSymbolsResponse:
        query: dict[str, Any] = {}
        if self._has_field(request, "market"):
            query["market"] = request.market

        payload = self._get("/api/v2/symbols", query)
        symbols = payload if isinstance(payload, list) else []
        return self._parse_message({"symbols": symbols}, pb.ListSymbolsResponse)

    def GetFiat(
        self, request: pb.GetFiatRequest, context: Any = None
    ) -> pb.GetFiatResponse:
        query: dict[str, Any] = {}
        if self._has_field(request, "base"):
            query["base"] = request.base
        if self._has_field(request, "currencies"):
            query["currencies"] = request.currencies

        payload = self._get("/api/v1/prices", query)
        # payload is a dict like {"BTC": "64500.0", "ETH": "3200.0", ...}
        prices = []
        if isinstance(payload, dict):
            for currency, price in payload.items():
                prices.append({"currency": currency, "price": str(price)})
        return self._parse_message({"prices": prices}, pb.GetFiatResponse)

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

        # KuCoin wraps all responses in {"code":"200000","data":{...}}
        if isinstance(payload, dict) and "data" in payload:
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
        """Transform raw orderbook data: convert [["price", "size"], ...] lists to dicts."""
        for side in ("bids", "asks"):
            levels = data.get(side, [])
            parsed: list[dict[str, str]] = []
            for row in levels:
                if isinstance(row, list) and len(row) >= 2:
                    parsed.append({"price": str(row[0]), "size": str(row[1])})
            data[side] = parsed

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
