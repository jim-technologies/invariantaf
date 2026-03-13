"""DydxService — wraps the dYdX v4 Indexer REST API into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from dydx_mcp.gen.dydx.v1 import dydx_pb2 as pb

_BASE_URL = "https://indexer.dydx.trade/v4"

# Map proto CandleResolution enum to dYdX API resolution strings.
_RESOLUTION_MAP = {
    pb.CANDLE_RESOLUTION_1MIN: "1MIN",
    pb.CANDLE_RESOLUTION_5MINS: "5MINS",
    pb.CANDLE_RESOLUTION_15MINS: "15MINS",
    pb.CANDLE_RESOLUTION_30MINS: "30MINS",
    pb.CANDLE_RESOLUTION_1HOUR: "1HOUR",
    pb.CANDLE_RESOLUTION_4HOURS: "4HOURS",
    pb.CANDLE_RESOLUTION_1DAY: "1DAY",
}

# Map dYdX API side strings to proto TradeSide enum.
_SIDE_MAP = {
    "BUY": pb.TRADE_SIDE_BUY,
    "SELL": pb.TRADE_SIDE_SELL,
}


class DydxService:
    """Implements DydxService RPCs via the free dYdX v4 Indexer API."""

    def __init__(self, base_url: str = _BASE_URL):
        self._base_url = base_url
        self._http = httpx.Client(timeout=30)

    def _get(self, path: str, params: dict | None = None) -> Any:
        resp = self._http.get(f"{self._base_url}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def ListMarkets(self, request: Any, context: Any = None) -> pb.ListMarketsResponse:
        params = {}
        ticker = getattr(request, "ticker", "") or ""
        limit = getattr(request, "limit", 0) or 0
        if ticker:
            params["ticker"] = ticker
        if limit > 0:
            params["limit"] = limit

        raw = self._get("/perpetualMarkets", params=params or None)
        markets_data = raw.get("markets", {})

        markets = []
        for _key, m in markets_data.items():
            markets.append(pb.PerpetualMarket(
                ticker=m.get("ticker", ""),
                status=m.get("status", ""),
                oracle_price=m.get("oraclePrice", ""),
                price_change_24h=m.get("priceChange24H", ""),
                volume_24h=m.get("volume24H", ""),
                open_interest=m.get("openInterest", ""),
                next_funding_rate=m.get("nextFundingRate", ""),
                step_size=m.get("stepSize", ""),
                tick_size=m.get("tickSize", ""),
                initial_margin_fraction=m.get("initialMarginFraction", ""),
                maintenance_margin_fraction=m.get("maintenanceMarginFraction", ""),
                open_interest_usd=m.get("openInterestUSDC", ""),
            ))

        return pb.ListMarketsResponse(markets=markets)

    def GetOrderbook(self, request: Any, context: Any = None) -> pb.GetOrderbookResponse:
        ticker = request.ticker if hasattr(request, "ticker") else "BTC-USD"
        raw = self._get(f"/orderbooks/perpetualMarket/{ticker}")

        bids = []
        for bid in raw.get("bids", []):
            bids.append(pb.OrderbookLevel(
                price=bid.get("price", ""),
                size=bid.get("size", ""),
            ))

        asks = []
        for ask in raw.get("asks", []):
            asks.append(pb.OrderbookLevel(
                price=ask.get("price", ""),
                size=ask.get("size", ""),
            ))

        return pb.GetOrderbookResponse(bids=bids, asks=asks)

    def GetTrades(self, request: Any, context: Any = None) -> pb.GetTradesResponse:
        ticker = request.ticker if hasattr(request, "ticker") else "BTC-USD"
        params = {}
        limit = getattr(request, "limit", 0) or 0
        if limit > 0:
            params["limit"] = limit

        raw = self._get(f"/trades/perpetualMarket/{ticker}", params=params or None)

        trades = []
        for t in raw.get("trades", []):
            side = _SIDE_MAP.get(t.get("side", ""), pb.TRADE_SIDE_UNSPECIFIED)
            trades.append(pb.Trade(
                id=t.get("id", ""),
                side=side,
                price=t.get("price", ""),
                size=t.get("size", ""),
                created_at=t.get("createdAt", ""),
            ))

        return pb.GetTradesResponse(trades=trades)

    def GetCandles(self, request: Any, context: Any = None) -> pb.GetCandlesResponse:
        ticker = request.ticker if hasattr(request, "ticker") else "BTC-USD"
        resolution = _RESOLUTION_MAP.get(
            getattr(request, "resolution", pb.CANDLE_RESOLUTION_UNSPECIFIED),
            "1HOUR",
        )
        params = {"resolution": resolution}
        limit = getattr(request, "limit", 0) or 0
        if limit > 0:
            params["limit"] = limit

        raw = self._get(f"/candles/perpetualMarkets/{ticker}", params=params)

        candles = []
        for c in raw.get("candles", []):
            candles.append(pb.Candle(
                started_at=c.get("startedAt", ""),
                open=c.get("open", ""),
                high=c.get("high", ""),
                low=c.get("low", ""),
                close=c.get("close", ""),
                base_token_volume=c.get("baseTokenVolume", ""),
                usd_volume=c.get("usdVolume", ""),
                trades=int(c.get("trades", 0)),
                resolution=c.get("resolution", ""),
            ))

        return pb.GetCandlesResponse(candles=candles)

    def GetFundingRates(self, request: Any, context: Any = None) -> pb.GetFundingRatesResponse:
        ticker = request.ticker if hasattr(request, "ticker") else "BTC-USD"
        params = {}
        limit = getattr(request, "limit", 0) or 0
        if limit > 0:
            params["limit"] = limit

        raw = self._get(f"/historicalFunding/{ticker}", params=params or None)

        funding_rates = []
        for fr in raw.get("historicalFunding", []):
            funding_rates.append(pb.FundingRate(
                ticker=fr.get("ticker", ""),
                rate=fr.get("rate", ""),
                price=fr.get("price", ""),
                effective_at=fr.get("effectiveAt", ""),
            ))

        return pb.GetFundingRatesResponse(funding_rates=funding_rates)
