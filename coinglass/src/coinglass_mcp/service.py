"""CoinGlassService -- wraps the CoinGlass API into proto RPCs."""

from __future__ import annotations

import os
from typing import Any

import httpx

from coinglass_mcp.gen.coinglass.v1 import coinglass_pb2 as pb

_BASE_URL = "https://open-api.coinglass.com/public/v2"


class CoinGlassService:
    """Implements CoinGlassService RPCs via the CoinGlass public API."""

    def __init__(self):
        headers = {}
        api_key = os.environ.get("COINGLASS_API_KEY")
        if api_key:
            headers["coinglassSecret"] = api_key
        self._http = httpx.Client(timeout=30, headers=headers)

    def _get(self, path: str, params: dict | None = None) -> Any:
        resp = self._http.get(f"{_BASE_URL}{path}", params=params)
        resp.raise_for_status()
        body = resp.json()
        # CoinGlass wraps responses in {"code": "0", "msg": "...", "data": ...}.
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body

    def GetFundingRate(self, request: Any, context: Any = None) -> pb.GetFundingRateResponse:
        params = {}
        if request.symbol:
            params["symbol"] = request.symbol
        raw = self._get("/funding", params=params or None)
        resp = pb.GetFundingRateResponse()
        if isinstance(raw, list):
            for item in raw:
                resp.data.append(_parse_funding_rate(item))
        elif isinstance(raw, dict):
            resp.data.append(_parse_funding_rate(raw))
        return resp

    def GetOpenInterest(self, request: Any, context: Any = None) -> pb.GetOpenInterestResponse:
        params = {"symbol": request.symbol} if request.symbol else {}
        raw = self._get("/open_interest", params=params or None)
        oi_data = _parse_open_interest(raw, request.symbol)
        return pb.GetOpenInterestResponse(data=oi_data)

    def GetLiquidation(self, request: Any, context: Any = None) -> pb.GetLiquidationResponse:
        params = {}
        if request.symbol:
            params["symbol"] = request.symbol
        time_type = request.time_type if request.time_type else "all"
        params["time_type"] = time_type
        raw = self._get("/liquidation_history", params=params)
        resp = pb.GetLiquidationResponse()
        if isinstance(raw, list):
            for item in raw:
                resp.records.append(_parse_liquidation(item))
        return resp

    def GetLongShortRatio(self, request: Any, context: Any = None) -> pb.GetLongShortRatioResponse:
        params = {}
        if request.symbol:
            params["symbol"] = request.symbol
        time_type = request.time_type if request.time_type else "all"
        params["time_type"] = time_type
        raw = self._get("/long_short", params=params)
        resp = pb.GetLongShortRatioResponse()
        if isinstance(raw, list):
            for item in raw:
                resp.records.append(_parse_long_short(item))
        return resp

    def GetOIHistory(self, request: Any, context: Any = None) -> pb.GetOIHistoryResponse:
        params = {}
        if request.symbol:
            params["symbol"] = request.symbol
        time_type = request.time_type if request.time_type else "all"
        params["time_type"] = time_type
        raw = self._get("/open_interest_history", params=params)
        resp = pb.GetOIHistoryResponse()
        if isinstance(raw, list):
            for item in raw:
                resp.records.append(_parse_oi_history(item))
        return resp


def _parse_funding_rate(item: dict) -> pb.FundingRateData:
    """Parse a raw CoinGlass funding rate JSON object."""
    symbol = item.get("symbol", "") or ""
    exchanges = []
    # CoinGlass may nest exchange data under various keys.
    for key in ("exchangeList", "exchanges"):
        if key in item and isinstance(item[key], list):
            for ex in item[key]:
                exchanges.append(pb.ExchangeFundingRate(
                    exchange=ex.get("exchange", "") or ex.get("exchangeName", "") or "",
                    rate=ex.get("rate", 0) or ex.get("fundingRate", 0) or 0,
                    predicted_rate=ex.get("predictedRate", 0) or ex.get("nextFundingRate", 0) or 0,
                ))
            break
    return pb.FundingRateData(symbol=symbol, exchanges=exchanges)


def _parse_open_interest(raw: Any, symbol: str = "") -> pb.OpenInterestData:
    """Parse a raw CoinGlass open interest JSON object."""
    exchanges = []
    if isinstance(raw, list):
        for ex in raw:
            exchanges.append(pb.ExchangeOpenInterest(
                exchange=ex.get("exchange", "") or ex.get("exchangeName", "") or "",
                open_interest_usd=ex.get("openInterest", 0) or ex.get("openInterestUsd", 0) or 0,
                open_interest_amount=ex.get("openInterestAmount", 0) or ex.get("openInterestCoin", 0) or 0,
            ))
    elif isinstance(raw, dict):
        for key in ("exchangeList", "exchanges"):
            if key in raw and isinstance(raw[key], list):
                for ex in raw[key]:
                    exchanges.append(pb.ExchangeOpenInterest(
                        exchange=ex.get("exchange", "") or ex.get("exchangeName", "") or "",
                        open_interest_usd=ex.get("openInterest", 0) or ex.get("openInterestUsd", 0) or 0,
                        open_interest_amount=ex.get("openInterestAmount", 0) or ex.get("openInterestCoin", 0) or 0,
                    ))
                break
        symbol = raw.get("symbol", symbol) or symbol
    return pb.OpenInterestData(symbol=symbol, exchanges=exchanges)


def _parse_liquidation(item: dict) -> pb.LiquidationRecord:
    """Parse a raw CoinGlass liquidation record."""
    return pb.LiquidationRecord(
        timestamp=item.get("timestamp", 0) or item.get("t", 0) or 0,
        long_liquidation_usd=item.get("longLiquidationUsd", 0) or item.get("longVolUsd", 0) or 0,
        short_liquidation_usd=item.get("shortLiquidationUsd", 0) or item.get("shortVolUsd", 0) or 0,
        long_count=item.get("longCount", 0) or item.get("longNum", 0) or 0,
        short_count=item.get("shortCount", 0) or item.get("shortNum", 0) or 0,
    )


def _parse_long_short(item: dict) -> pb.LongShortRecord:
    """Parse a raw CoinGlass long/short ratio record."""
    return pb.LongShortRecord(
        timestamp=item.get("timestamp", 0) or item.get("t", 0) or 0,
        long_rate=item.get("longRate", 0) or item.get("longRatio", 0) or 0,
        short_rate=item.get("shortRate", 0) or item.get("shortRatio", 0) or 0,
        long_short_ratio=item.get("longShortRatio", 0) or item.get("ratio", 0) or 0,
    )


def _parse_oi_history(item: dict) -> pb.OIHistoryRecord:
    """Parse a raw CoinGlass OI history record."""
    return pb.OIHistoryRecord(
        timestamp=item.get("timestamp", 0) or item.get("t", 0) or 0,
        open_interest_usd=item.get("openInterest", 0) or item.get("openInterestUsd", 0) or 0,
    )
