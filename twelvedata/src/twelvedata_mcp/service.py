"""Twelve Data market data service implementation for Invariant Protocol."""

from __future__ import annotations

import os
import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from twelvedata_mcp.gen.twelvedata.v1 import twelvedata_pb2 as pb

DEFAULT_BASE_URL = "https://api.twelvedata.com"


class TwelveDataService:
    """Implements TwelveDataService -- stocks, forex, crypto market data endpoints."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        timeout: float = 15.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key or os.getenv("TWELVEDATA_API_KEY", "")
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    # -------------------------
    # RPC handlers
    # -------------------------

    def GetQuote(
        self, request: pb.GetQuoteRequest, context: Any = None
    ) -> pb.GetQuoteResponse:
        query: dict[str, Any] = {"symbol": request.symbol}
        payload = self._get("/quote", query)
        return self._parse_message(self._normalize_quote(payload), pb.GetQuoteResponse)

    def GetTimeSeries(
        self, request: pb.GetTimeSeriesRequest, context: Any = None
    ) -> pb.GetTimeSeriesResponse:
        query: dict[str, Any] = {
            "symbol": request.symbol,
            "interval": request.interval,
        }
        if self._has_field(request, "outputsize"):
            query["outputsize"] = request.outputsize

        payload = self._get("/time_series", query)
        return self._parse_message(self._normalize_time_series(payload), pb.GetTimeSeriesResponse)

    def GetPrice(
        self, request: pb.GetPriceRequest, context: Any = None
    ) -> pb.GetPriceResponse:
        query: dict[str, Any] = {"symbol": request.symbol}
        payload = self._get("/price", query)
        price = self._safe_float(payload.get("price", 0))
        return self._parse_message({"price": price}, pb.GetPriceResponse)

    def ListStocks(
        self, request: pb.ListStocksRequest, context: Any = None
    ) -> pb.ListStocksResponse:
        query: dict[str, Any] = {}
        if self._has_field(request, "exchange"):
            query["exchange"] = request.exchange

        payload = self._get("/stocks", query)
        stocks = self._extract_data_list(payload)
        return self._parse_message({"stocks": stocks}, pb.ListStocksResponse)

    def ListForexPairs(
        self, request: pb.ListForexPairsRequest, context: Any = None
    ) -> pb.ListForexPairsResponse:
        payload = self._get("/forex_pairs", {})
        pairs = self._extract_data_list(payload)
        return self._parse_message({"pairs": pairs}, pb.ListForexPairsResponse)

    def ListCryptoPairs(
        self, request: pb.ListCryptoPairsRequest, context: Any = None
    ) -> pb.ListCryptoPairsResponse:
        payload = self._get("/cryptocurrencies", {})
        pairs = self._extract_data_list(payload)
        return self._parse_message({"pairs": pairs}, pb.ListCryptoPairsResponse)

    def GetExchangeRate(
        self, request: pb.GetExchangeRateRequest, context: Any = None
    ) -> pb.GetExchangeRateResponse:
        query: dict[str, Any] = {"symbol": request.symbol}
        payload = self._get("/exchange_rate", query)
        return self._parse_message(
            self._normalize_exchange_rate(payload), pb.GetExchangeRateResponse
        )

    def GetEarningsCalendar(
        self, request: pb.GetEarningsCalendarRequest, context: Any = None
    ) -> pb.GetEarningsCalendarResponse:
        query: dict[str, Any] = {}
        if self._has_field(request, "start_date"):
            query["start_date"] = request.start_date
        if self._has_field(request, "end_date"):
            query["end_date"] = request.end_date

        payload = self._get("/earnings", query)
        earnings = self._extract_earnings(payload)
        return self._parse_message({"earnings": earnings}, pb.GetEarningsCalendarResponse)

    # -------------------------
    # Response normalization
    # -------------------------

    def _normalize_quote(self, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize Twelve Data /quote response to proto fields."""
        return {
            "symbol": data.get("symbol", ""),
            "name": data.get("name", ""),
            "exchange": data.get("exchange", ""),
            "currency": data.get("currency", ""),
            "open": self._safe_float(data.get("open", 0)),
            "high": self._safe_float(data.get("high", 0)),
            "low": self._safe_float(data.get("low", 0)),
            "close": self._safe_float(data.get("close", 0)),
            "previous_close": self._safe_float(data.get("previous_close", 0)),
            "change": self._safe_float(data.get("change", 0)),
            "percent_change": self._safe_float(data.get("percent_change", 0)),
            "volume": self._safe_int(data.get("volume", 0)),
            "datetime": data.get("datetime", ""),
            "timestamp": str(data.get("timestamp", "")),
            "fifty_two_week_high": self._safe_float(data.get("fifty_two_week", {}).get("high", 0) if isinstance(data.get("fifty_two_week"), dict) else 0),
            "fifty_two_week_low": self._safe_float(data.get("fifty_two_week", {}).get("low", 0) if isinstance(data.get("fifty_two_week"), dict) else 0),
        }

    def _normalize_time_series(self, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize Twelve Data /time_series response."""
        meta = data.get("meta", {})
        values_raw = data.get("values", [])
        values = []
        for v in values_raw:
            values.append({
                "datetime": v.get("datetime", ""),
                "open": self._safe_float(v.get("open", 0)),
                "high": self._safe_float(v.get("high", 0)),
                "low": self._safe_float(v.get("low", 0)),
                "close": self._safe_float(v.get("close", 0)),
                "volume": self._safe_int(v.get("volume", 0)),
            })
        return {
            "symbol": meta.get("symbol", ""),
            "interval": meta.get("interval", ""),
            "currency": meta.get("currency", ""),
            "exchange": meta.get("exchange", ""),
            "type": meta.get("type", ""),
            "values": values,
        }

    def _normalize_exchange_rate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize Twelve Data /exchange_rate response."""
        return {
            "symbol": data.get("symbol", ""),
            "rate": self._safe_float(data.get("rate", 0)),
            "timestamp": str(data.get("timestamp", "")),
        }

    def _extract_data_list(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract the 'data' list from Twelve Data list endpoints."""
        data = payload.get("data", [])
        if isinstance(data, list):
            return data
        return []

    def _extract_earnings(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract and normalize earnings events."""
        earnings_raw = payload.get("earnings", [])
        if not isinstance(earnings_raw, list):
            return []
        result = []
        for e in earnings_raw:
            result.append({
                "symbol": e.get("symbol", ""),
                "name": e.get("name", ""),
                "currency": e.get("currency", ""),
                "exchange": e.get("exchange", ""),
                "country": e.get("country", ""),
                "date": e.get("date", ""),
                "time": e.get("time", ""),
                "eps_estimate": self._safe_float(e.get("eps_estimate", 0)),
                "eps_actual": self._safe_float(e.get("eps_actual", 0)),
                "revenue_estimate": self._safe_float(e.get("revenue_estimate", 0)),
                "revenue_actual": self._safe_float(e.get("revenue_actual", 0)),
            })
        return result

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

        # Check for Twelve Data API-level errors
        if isinstance(payload, dict) and payload.get("status") == "error":
            raise RuntimeError(
                f"GET {url}: API error: {payload.get('message', 'unknown error')}"
            )

        return payload

    def _build_url(self, path: str, query: dict[str, Any] | None = None) -> str:
        full = f"{self._base_url}{path}"
        params: list[tuple[str, str]] = []
        if query:
            params.extend(
                (k, self._to_http_scalar(v)) for k, v in query.items() if v is not None
            )
        # Always append the API key
        if self._api_key:
            params.append(("apikey", self._api_key))
        if not params:
            return full
        qs = urllib.parse.urlencode(params)
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

    def _safe_float(self, value: Any) -> float:
        """Convert a value to float, returning 0.0 for None or non-numeric strings."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _safe_int(self, value: Any) -> int:
        """Convert a value to int, returning 0 for None or non-numeric strings."""
        if value is None:
            return 0
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return 0
