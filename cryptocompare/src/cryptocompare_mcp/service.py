"""CryptoCompare market data service implementation for Invariant Protocol."""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from cryptocompare_mcp.gen.cryptocompare.v1 import cryptocompare_pb2 as pb

DEFAULT_BASE_URL = "https://min-api.cryptocompare.com"


class CryptoCompareService:
    """Implements CryptoCompareService -- public market data endpoints (no auth required)."""

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

    def GetPrice(
        self, request: pb.GetPriceRequest, context: Any = None
    ) -> pb.GetPriceResponse:
        query: dict[str, Any] = {
            "fsym": request.fsym,
            "tsyms": request.tsyms,
        }

        payload = self._get("/data/price", query)
        # Response is like {"USD": 64500, "EUR": 59000}
        prices = {k: float(v) for k, v in payload.items() if isinstance(v, (int, float))}
        return self._parse_message({"prices": prices}, pb.GetPriceResponse)

    def GetMultiPrice(
        self, request: pb.GetMultiPriceRequest, context: Any = None
    ) -> pb.GetMultiPriceResponse:
        query: dict[str, Any] = {
            "fsyms": request.fsyms,
            "tsyms": request.tsyms,
        }

        payload = self._get("/data/pricemulti", query)
        # Response is like {"BTC": {"USD": 64500}, "ETH": {"USD": 2500}}
        rows = []
        for from_sym, prices_map in payload.items():
            if isinstance(prices_map, dict):
                prices = {k: float(v) for k, v in prices_map.items() if isinstance(v, (int, float))}
                rows.append({"from_symbol": from_sym, "prices": prices})
        return self._parse_message({"rows": rows}, pb.GetMultiPriceResponse)

    def GetFullPrice(
        self, request: pb.GetFullPriceRequest, context: Any = None
    ) -> pb.GetFullPriceResponse:
        query: dict[str, Any] = {
            "fsyms": request.fsyms,
            "tsyms": request.tsyms,
        }

        payload = self._get("/data/pricemultifull", query)
        # Response is {"RAW": {"BTC": {"USD": {...fields...}}}}
        raw = payload.get("RAW", {})
        coins = []
        for from_sym, to_map in raw.items():
            if isinstance(to_map, dict):
                for to_sym, data in to_map.items():
                    if isinstance(data, dict):
                        coins.append({
                            "from_symbol": from_sym,
                            "to_symbol": to_sym,
                            "price": data.get("PRICE", 0.0),
                            "volume_24h": data.get("VOLUME24HOUR", 0.0),
                            "market_cap": data.get("MKTCAP", 0.0),
                            "change_pct_24h": data.get("CHANGEPCT24HOUR", 0.0),
                            "high_24h": data.get("HIGH24HOUR", 0.0),
                            "low_24h": data.get("LOW24HOUR", 0.0),
                            "open_24h": data.get("OPEN24HOUR", 0.0),
                            "supply": data.get("SUPPLY", 0.0),
                        })
        return self._parse_message({"coins": coins}, pb.GetFullPriceResponse)

    def GetHistoHour(
        self, request: pb.GetHistoHourRequest, context: Any = None
    ) -> pb.GetHistoHourResponse:
        query: dict[str, Any] = {
            "fsym": request.fsym,
            "tsym": request.tsym,
        }
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        payload = self._get("/data/v2/histohour", query)
        # Response is {"Data": {"Data": [{...ohlcv...}]}}
        candles = self._extract_histo_data(payload)
        return self._parse_message({"candles": candles}, pb.GetHistoHourResponse)

    def GetHistoDay(
        self, request: pb.GetHistoDayRequest, context: Any = None
    ) -> pb.GetHistoDayResponse:
        query: dict[str, Any] = {
            "fsym": request.fsym,
            "tsym": request.tsym,
        }
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        payload = self._get("/data/v2/histoday", query)
        # Response is {"Data": {"Data": [{...ohlcv...}]}}
        candles = self._extract_histo_data(payload)
        return self._parse_message({"candles": candles}, pb.GetHistoDayResponse)

    def GetTopByVolume(
        self, request: pb.GetTopByVolumeRequest, context: Any = None
    ) -> pb.GetTopByVolumeResponse:
        query: dict[str, Any] = {
            "tsym": request.tsym,
        }
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        payload = self._get("/data/top/totalvolfull", query)
        # Response is {"Data": [{...}]}
        data = payload.get("Data", [])
        coins = []
        for item in data:
            if not isinstance(item, dict):
                continue
            coin_info = item.get("CoinInfo", {})
            raw_data = item.get("RAW", {})
            tsym_data = raw_data.get(request.tsym, {}) if isinstance(raw_data, dict) else {}
            coins.append({
                "name": coin_info.get("FullName", ""),
                "symbol": coin_info.get("Name", ""),
                "price": tsym_data.get("PRICE", 0.0),
                "volume_24h": tsym_data.get("VOLUME24HOUR", 0.0),
                "market_cap": tsym_data.get("MKTCAP", 0.0),
                "change_pct_24h": tsym_data.get("CHANGEPCT24HOUR", 0.0),
            })
        return self._parse_message({"coins": coins}, pb.GetTopByVolumeResponse)

    # -------------------------
    # Data extraction
    # -------------------------

    def _extract_histo_data(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract OHLCV candles from CryptoCompare's nested response."""
        data_wrapper = payload.get("Data", {})
        if isinstance(data_wrapper, dict):
            raw_candles = data_wrapper.get("Data", [])
        else:
            raw_candles = []

        candles = []
        for c in raw_candles:
            if isinstance(c, dict):
                candles.append({
                    "time": c.get("time", 0),
                    "open": c.get("open", 0.0),
                    "high": c.get("high", 0.0),
                    "low": c.get("low", 0.0),
                    "close": c.get("close", 0.0),
                    "volumefrom": c.get("volumefrom", 0.0),
                    "volumeto": c.get("volumeto", 0.0),
                })
        return candles

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

    def _parse_message(self, payload: dict[str, Any], message_cls: type):
        message = message_cls()
        json_format.ParseDict(payload, message, ignore_unknown_fields=True)
        return message

    def _has_field(self, message: Any, field_name: str) -> bool:
        try:
            return bool(message.HasField(field_name))
        except ValueError:
            return False
