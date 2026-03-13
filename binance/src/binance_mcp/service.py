"""Binance Spot public market data service implementation for Invariant Protocol."""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from binance_mcp.gen.binance.v1 import binance_pb2 as pb

DEFAULT_BASE_URL = "https://api.binance.com"


class BinanceService:
    """Implements BinanceMarketService -- public market data endpoints (no auth required)."""

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

    def GetPrice(self, request: pb.GetPriceRequest, context: Any = None) -> pb.GetPriceResponse:
        query: dict[str, Any] = {}
        if self._has_field(request, "symbol"):
            query["symbol"] = request.symbol

        payload = self._get("/api/v3/ticker/price", query)

        # Normalize: single object -> list
        if isinstance(payload, dict):
            payload = [payload]

        return self._parse_message({"prices": payload}, pb.GetPriceResponse)

    def Get24hrStats(self, request: pb.Get24hrStatsRequest, context: Any = None) -> pb.Get24hrStatsResponse:
        query: dict[str, Any] = {}
        if self._has_field(request, "symbol"):
            query["symbol"] = request.symbol

        payload = self._get("/api/v3/ticker/24hr", query)

        # Normalize: single object -> list
        if isinstance(payload, dict):
            payload = [payload]

        tickers = []
        for item in payload:
            tickers.append(self._normalize_24hr(item))

        return self._parse_message({"tickers": tickers}, pb.Get24hrStatsResponse)

    def GetOrderbook(self, request: pb.GetOrderbookRequest, context: Any = None) -> pb.GetOrderbookResponse:
        query: dict[str, Any] = {"symbol": request.symbol}
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        payload = self._get("/api/v3/depth", query)
        self._transform_orderbook(payload)
        return self._parse_message(payload, pb.GetOrderbookResponse)

    def GetKlines(self, request: pb.GetKlinesRequest, context: Any = None) -> pb.GetKlinesResponse:
        query: dict[str, Any] = {
            "symbol": request.symbol,
            "interval": request.interval,
        }
        if self._has_field(request, "start_time"):
            query["startTime"] = request.start_time
        if self._has_field(request, "end_time"):
            query["endTime"] = request.end_time
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        payload = self._get("/api/v3/klines", query)

        klines = []
        for row in payload:
            klines.append(self._transform_kline(row))

        return self._parse_message({"klines": klines}, pb.GetKlinesResponse)

    def GetTrades(self, request: pb.GetTradesRequest, context: Any = None) -> pb.GetTradesResponse:
        query: dict[str, Any] = {"symbol": request.symbol}
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        payload = self._get("/api/v3/trades", query)

        trades = []
        for item in payload:
            trades.append(self._normalize_trade(item))

        return self._parse_message({"trades": trades}, pb.GetTradesResponse)

    def GetExchangeInfo(
        self, request: pb.GetExchangeInfoRequest, context: Any = None
    ) -> pb.GetExchangeInfoResponse:
        query: dict[str, Any] = {}
        if self._has_field(request, "symbol"):
            query["symbol"] = request.symbol

        payload = self._get("/api/v3/exchangeInfo", query)
        self._transform_exchange_info(payload)
        return self._parse_message(payload, pb.GetExchangeInfoResponse)

    def GetAvgPrice(self, request: pb.GetAvgPriceRequest, context: Any = None) -> pb.GetAvgPriceResponse:
        query: dict[str, Any] = {"symbol": request.symbol}
        payload = self._get("/api/v3/avgPrice", query)
        return self._parse_message(payload, pb.GetAvgPriceResponse)

    def GetBookTicker(self, request: pb.GetBookTickerRequest, context: Any = None) -> pb.GetBookTickerResponse:
        query: dict[str, Any] = {}
        if self._has_field(request, "symbol"):
            query["symbol"] = request.symbol

        payload = self._get("/api/v3/ticker/bookTicker", query)

        # Normalize: single object -> list
        if isinstance(payload, dict):
            payload = [payload]

        tickers = []
        for item in payload:
            tickers.append(self._normalize_book_ticker(item))

        return self._parse_message({"tickers": tickers}, pb.GetBookTickerResponse)

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

    def _normalize_24hr(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "symbol": item.get("symbol", ""),
            "price_change": str(item.get("priceChange", "")),
            "price_change_percent": str(item.get("priceChangePercent", "")),
            "weighted_avg_price": str(item.get("weightedAvgPrice", "")),
            "prev_close_price": str(item.get("prevClosePrice", "")),
            "last_price": str(item.get("lastPrice", "")),
            "last_qty": str(item.get("lastQty", "")),
            "bid_price": str(item.get("bidPrice", "")),
            "bid_qty": str(item.get("bidQty", "")),
            "ask_price": str(item.get("askPrice", "")),
            "ask_qty": str(item.get("askQty", "")),
            "open_price": str(item.get("openPrice", "")),
            "high_price": str(item.get("highPrice", "")),
            "low_price": str(item.get("lowPrice", "")),
            "volume": str(item.get("volume", "")),
            "quote_volume": str(item.get("quoteVolume", "")),
            "open_time": item.get("openTime", 0),
            "close_time": item.get("closeTime", 0),
            "first_id": item.get("firstId", 0),
            "last_id": item.get("lastId", 0),
            "count": item.get("count", 0),
        }

    def _transform_orderbook(self, payload: dict[str, Any]) -> None:
        for side in ("bids", "asks"):
            levels = payload.get(side, [])
            parsed: list[dict[str, str]] = []
            for row in levels:
                if isinstance(row, list) and len(row) >= 2:
                    parsed.append({"price": str(row[0]), "quantity": str(row[1])})
            payload[side] = parsed
        # Rename lastUpdateId -> last_update_id
        if "lastUpdateId" in payload:
            payload["last_update_id"] = payload.pop("lastUpdateId")

    def _transform_kline(self, row: list) -> dict[str, Any]:
        return {
            "open_time": row[0] if len(row) > 0 else 0,
            "open": str(row[1]) if len(row) > 1 else "",
            "high": str(row[2]) if len(row) > 2 else "",
            "low": str(row[3]) if len(row) > 3 else "",
            "close": str(row[4]) if len(row) > 4 else "",
            "volume": str(row[5]) if len(row) > 5 else "",
            "close_time": row[6] if len(row) > 6 else 0,
            "quote_asset_volume": str(row[7]) if len(row) > 7 else "",
            "number_of_trades": row[8] if len(row) > 8 else 0,
            "taker_buy_base_asset_volume": str(row[9]) if len(row) > 9 else "",
            "taker_buy_quote_asset_volume": str(row[10]) if len(row) > 10 else "",
        }

    def _normalize_trade(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": item.get("id", 0),
            "price": str(item.get("price", "")),
            "qty": str(item.get("qty", "")),
            "quote_qty": str(item.get("quoteQty", "")),
            "time": item.get("time", 0),
            "is_buyer_maker": item.get("isBuyerMaker", False),
            "is_best_match": item.get("isBestMatch", False),
        }

    def _transform_exchange_info(self, payload: dict[str, Any]) -> None:
        # Rename serverTime -> server_time
        if "serverTime" in payload:
            payload["server_time"] = payload.pop("serverTime")

        # Rename rateLimits -> rate_limits and transform
        raw_limits = payload.pop("rateLimits", [])
        rate_limits = []
        for rl in raw_limits:
            rate_limits.append({
                "rate_limit_type": rl.get("rateLimitType", ""),
                "interval": rl.get("interval", ""),
                "interval_num": rl.get("intervalNum", 0),
                "limit": rl.get("limit", 0),
            })
        payload["rate_limits"] = rate_limits

        # Transform symbols
        raw_symbols = payload.pop("symbols", [])
        symbols = []
        for sym in raw_symbols:
            filters = []
            for f in sym.get("filters", []):
                filt: dict[str, Any] = {"filter_type": f.get("filterType", "")}
                if "minPrice" in f:
                    filt["min_price"] = f["minPrice"]
                if "maxPrice" in f:
                    filt["max_price"] = f["maxPrice"]
                if "tickSize" in f:
                    filt["tick_size"] = f["tickSize"]
                if "minQty" in f:
                    filt["min_qty"] = f["minQty"]
                if "maxQty" in f:
                    filt["max_qty"] = f["maxQty"]
                if "stepSize" in f:
                    filt["step_size"] = f["stepSize"]
                if "minNotional" in f:
                    filt["min_notional"] = f["minNotional"]
                filters.append(filt)

            symbols.append({
                "symbol": sym.get("symbol", ""),
                "status": sym.get("status", ""),
                "base_asset": sym.get("baseAsset", ""),
                "base_asset_precision": sym.get("baseAssetPrecision", 0),
                "quote_asset": sym.get("quoteAsset", ""),
                "quote_precision": sym.get("quotePrecision", 0),
                "order_types": sym.get("orderTypes", []),
                "iceberg_allowed": sym.get("icebergAllowed", False),
                "oco_allowed": sym.get("ocoAllowed", False),
                "is_spot_trading_allowed": sym.get("isSpotTradingAllowed", False),
                "is_margin_trading_allowed": sym.get("isMarginTradingAllowed", False),
                "filters": filters,
                "permissions": sym.get("permissions", []),
            })
        payload["symbols"] = symbols

        # Remove extra keys not in our proto
        for key in list(payload.keys()):
            if key not in ("timezone", "server_time", "rate_limits", "symbols"):
                del payload[key]

    def _normalize_book_ticker(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "symbol": item.get("symbol", ""),
            "bid_price": str(item.get("bidPrice", "")),
            "bid_qty": str(item.get("bidQty", "")),
            "ask_price": str(item.get("askPrice", "")),
            "ask_qty": str(item.get("askQty", "")),
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
