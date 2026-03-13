"""Deribit public market data service implementation for Invariant Protocol."""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from deribit_mcp.gen.deribit.v1 import deribit_pb2 as pb

DEFAULT_BASE_URL = "https://www.deribit.com"


class DeribitService:
    """Implements DeribitService -- public market data endpoints (no auth required)."""

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
        query: dict[str, Any] = {"currency": request.currency}
        if self._has_field(request, "kind"):
            query["kind"] = request.kind
        if self._has_field(request, "expired"):
            query["expired"] = request.expired

        payload = self._get("/api/v2/public/get_instruments", query)
        instruments = payload if isinstance(payload, list) else payload.get("result", payload)
        if isinstance(instruments, list):
            return self._parse_message({"instruments": instruments}, pb.GetInstrumentsResponse)
        return self._parse_message({"instruments": []}, pb.GetInstrumentsResponse)

    def GetOrderbook(
        self, request: pb.GetOrderbookRequest, context: Any = None
    ) -> pb.GetOrderbookResponse:
        query: dict[str, Any] = {"instrument_name": request.instrument_name}
        if self._has_field(request, "depth"):
            query["depth"] = request.depth

        payload = self._get("/api/v2/public/get_order_book", query)
        result = self._extract_result(payload)
        self._transform_orderbook(result)
        return self._parse_message(result, pb.GetOrderbookResponse)

    def GetTicker(
        self, request: pb.GetTickerRequest, context: Any = None
    ) -> pb.GetTickerResponse:
        query: dict[str, Any] = {"instrument_name": request.instrument_name}

        payload = self._get("/api/v2/public/ticker", query)
        result = self._extract_result(payload)
        self._transform_ticker(result)
        return self._parse_message(result, pb.GetTickerResponse)

    def GetBookSummaryByCurrency(
        self, request: pb.GetBookSummaryByCurrencyRequest, context: Any = None
    ) -> pb.GetBookSummaryByCurrencyResponse:
        query: dict[str, Any] = {"currency": request.currency}
        if self._has_field(request, "kind"):
            query["kind"] = request.kind

        payload = self._get("/api/v2/public/get_book_summary_by_currency", query)
        result = self._extract_result(payload)
        summaries = result if isinstance(result, list) else []
        transformed = []
        for s in summaries:
            transformed.append(self._transform_book_summary(s))
        return self._parse_message({"summaries": transformed}, pb.GetBookSummaryByCurrencyResponse)

    def GetHistoricalVolatility(
        self, request: pb.GetHistoricalVolatilityRequest, context: Any = None
    ) -> pb.GetHistoricalVolatilityResponse:
        query: dict[str, Any] = {"currency": request.currency}

        payload = self._get("/api/v2/public/get_historical_volatility", query)
        result = self._extract_result(payload)
        points = []
        if isinstance(result, list):
            for item in result:
                if isinstance(item, list) and len(item) >= 2:
                    points.append({"timestamp": int(item[0]), "volatility": float(item[1])})
        return self._parse_message({"data": points}, pb.GetHistoricalVolatilityResponse)

    def GetFundingRateValue(
        self, request: pb.GetFundingRateValueRequest, context: Any = None
    ) -> pb.GetFundingRateValueResponse:
        query: dict[str, Any] = {
            "instrument_name": request.instrument_name,
            "start_timestamp": request.start_timestamp,
            "end_timestamp": request.end_timestamp,
        }

        payload = self._get("/api/v2/public/get_funding_rate_value", query)
        result = self._extract_result(payload)
        if isinstance(result, (int, float)):
            return self._parse_message({"funding_rate": float(result)}, pb.GetFundingRateValueResponse)
        return self._parse_message({"funding_rate": 0.0}, pb.GetFundingRateValueResponse)

    def GetIndexPrice(
        self, request: pb.GetIndexPriceRequest, context: Any = None
    ) -> pb.GetIndexPriceResponse:
        query: dict[str, Any] = {"index_name": request.index_name}

        payload = self._get("/api/v2/public/get_index_price", query)
        result = self._extract_result(payload)
        return self._parse_message(result, pb.GetIndexPriceResponse)

    def GetTradingviewChartData(
        self, request: pb.GetTradingviewChartDataRequest, context: Any = None
    ) -> pb.GetTradingviewChartDataResponse:
        query: dict[str, Any] = {
            "instrument_name": request.instrument_name,
            "start_timestamp": request.start_timestamp,
            "end_timestamp": request.end_timestamp,
            "resolution": request.resolution,
        }

        payload = self._get("/api/v2/public/get_tradingview_chart_data", query)
        result = self._extract_result(payload)
        return self._parse_message(result, pb.GetTradingviewChartDataResponse)

    # -------------------------
    # Result extraction
    # -------------------------

    def _extract_result(self, payload: Any) -> Any:
        """Unwrap Deribit's ``{"jsonrpc":"2.0","result":...}`` envelope."""
        return payload.get("result", payload) if isinstance(payload, dict) else payload

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

        # Deribit wraps responses in {"jsonrpc":"2.0","result":...,"id":...}
        if isinstance(payload, dict) and "result" in payload:
            return payload

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
        """Transform raw orderbook data: convert [[price, amount], ...] lists to dicts."""
        for side in ("bids", "asks"):
            levels = data.get(side, [])
            parsed: list[dict[str, float]] = []
            for row in levels:
                if isinstance(row, list) and len(row) >= 2:
                    parsed.append({"price": float(row[0]), "amount": float(row[1])})
            data[side] = parsed

    def _transform_ticker(self, data: dict[str, Any]) -> None:
        """Flatten greeks from nested dict and normalize field names."""
        greeks_raw = data.pop("greeks", None)
        if greeks_raw and isinstance(greeks_raw, dict):
            data["greeks"] = greeks_raw

    def _transform_book_summary(self, item: dict[str, Any]) -> dict[str, Any]:
        """Normalize a book summary entry."""
        return {
            "instrument_name": item.get("instrument_name", ""),
            "volume_usd": item.get("volume_usd", 0.0),
            "open_interest": item.get("open_interest", 0.0),
            "bid_price": item.get("bid_price", 0.0),
            "ask_price": item.get("ask_price", 0.0),
            "last": item.get("last", 0.0),
            "mark_price": item.get("mark_price", 0.0),
            "mark_iv": item.get("mark_iv", 0.0),
            "underlying_price": item.get("underlying_price", 0.0),
            "underlying_index": item.get("underlying_index", ""),
            "interest_rate": item.get("interest_rate", 0.0),
            "funding_8h": item.get("funding_8h", 0.0),
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
