"""CoinPaprika public market data service implementation for Invariant Protocol."""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from coinpaprika_mcp.gen.coinpaprika.v1 import coinpaprika_pb2 as pb

DEFAULT_BASE_URL = "https://api.coinpaprika.com/v1"


class CoinPaprikaService:
    """Implements CoinPaprikaService -- public market data endpoints (no auth required)."""

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

    def GetGlobal(
        self, request: pb.GetGlobalRequest, context: Any = None
    ) -> pb.GetGlobalResponse:
        payload = self._get("/global")
        return self._parse_message(payload, pb.GetGlobalResponse)

    def ListCoins(
        self, request: pb.ListCoinsRequest, context: Any = None
    ) -> pb.ListCoinsResponse:
        payload = self._get("/coins")
        coins = payload if isinstance(payload, list) else []
        return self._parse_message({"coins": coins}, pb.ListCoinsResponse)

    def GetCoinById(
        self, request: pb.GetCoinByIdRequest, context: Any = None
    ) -> pb.GetCoinByIdResponse:
        coin_id = request.coin_id
        payload = self._get(f"/coins/{coin_id}")
        return self._parse_message(payload, pb.GetCoinByIdResponse)

    def GetTickerById(
        self, request: pb.GetTickerByIdRequest, context: Any = None
    ) -> pb.GetTickerByIdResponse:
        coin_id = request.coin_id
        payload = self._get(f"/tickers/{coin_id}")
        result = self._transform_ticker(payload)
        return self._parse_message(result, pb.GetTickerByIdResponse)

    def ListTickers(
        self, request: pb.ListTickersRequest, context: Any = None
    ) -> pb.ListTickersResponse:
        payload = self._get("/tickers")
        tickers_raw = payload if isinstance(payload, list) else []
        tickers = [self._transform_ticker(t) for t in tickers_raw]
        return self._parse_message({"tickers": tickers}, pb.ListTickersResponse)

    def GetCoinMarkets(
        self, request: pb.GetCoinMarketsRequest, context: Any = None
    ) -> pb.GetCoinMarketsResponse:
        coin_id = request.coin_id
        payload = self._get(f"/coins/{coin_id}/markets")
        markets_raw = payload if isinstance(payload, list) else []
        markets = [self._transform_market(m) for m in markets_raw]
        return self._parse_message({"markets": markets}, pb.GetCoinMarketsResponse)

    def GetCoinOHLCV(
        self, request: pb.GetCoinOHLCVRequest, context: Any = None
    ) -> pb.GetCoinOHLCVResponse:
        coin_id = request.coin_id
        payload = self._get(f"/coins/{coin_id}/ohlcv/latest/")
        entries = payload if isinstance(payload, list) else []
        return self._parse_message({"entries": entries}, pb.GetCoinOHLCVResponse)

    def SearchCoins(
        self, request: pb.SearchCoinsRequest, context: Any = None
    ) -> pb.SearchCoinsResponse:
        query: dict[str, Any] = {"q": request.query, "c": "currencies"}
        payload = self._get("/search/", query)
        currencies = []
        if isinstance(payload, dict):
            currencies = payload.get("currencies", [])
        return self._parse_message({"currencies": currencies}, pb.SearchCoinsResponse)

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

    def _transform_ticker(self, data: dict[str, Any]) -> dict[str, Any]:
        """Flatten quotes.USD into quotes_usd for protobuf mapping."""
        result = dict(data)
        quotes = result.pop("quotes", None)
        if isinstance(quotes, dict) and "USD" in quotes:
            result["quotes_usd"] = quotes["USD"]
        return result

    def _transform_market(self, data: dict[str, Any]) -> dict[str, Any]:
        """Flatten quotes.USD into quotes_usd for protobuf mapping."""
        result = dict(data)
        quotes = result.pop("quotes", None)
        if isinstance(quotes, dict) and "USD" in quotes:
            result["quotes_usd"] = quotes["USD"]
        return result

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
