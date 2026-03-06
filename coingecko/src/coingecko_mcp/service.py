"""CoinGeckoService — wraps the CoinGecko free API into proto RPCs."""

from __future__ import annotations

import os
from typing import Any

import httpx

from coingecko_mcp.gen.coingecko.v1 import coingecko_pb2 as pb

_BASE_URL = "https://api.coingecko.com/api/v3"


class CoinGeckoService:
    """Implements CoinGeckoService RPCs via the free CoinGecko API."""

    def __init__(self, *, api_key: str | None = None):
        self._http = httpx.Client(timeout=30)
        self._api_key = api_key or os.environ.get("COINGECKO_API_KEY")

    def _get(self, path: str, params: dict | None = None) -> Any:
        p = dict(params or {})
        if self._api_key:
            p["x_cg_demo_api_key"] = self._api_key
        resp = self._http.get(f"{_BASE_URL}{path}", params=p)
        resp.raise_for_status()
        return resp.json()

    def GetPrice(self, request: Any, context: Any = None) -> pb.GetPriceResponse:
        vs = request.vs_currency or "usd"
        params = {
            "ids": request.ids,
            "vs_currencies": vs,
            "include_market_cap": str(request.include_market_cap).lower(),
            "include_24hr_vol": str(request.include_24h_vol).lower(),
            "include_24hr_change": str(request.include_24h_change).lower(),
            "include_last_updated_at": "true",
        }
        raw = self._get("/simple/price", params)

        resp = pb.GetPriceResponse()
        for coin_id, data in raw.items():
            resp.prices.append(pb.CoinPrice(
                coin_id=coin_id,
                price=data.get(vs, 0),
                market_cap=data.get(f"{vs}_market_cap", 0),
                volume_24h=data.get(f"{vs}_24h_vol", 0),
                change_24h=data.get(f"{vs}_24h_change", 0),
                last_updated=data.get("last_updated_at", 0),
            ))
        return resp

    def Search(self, request: Any, context: Any = None) -> pb.SearchResponse:
        raw = self._get("/search", params={"query": request.query})
        resp = pb.SearchResponse()
        for c in raw.get("coins", []):
            resp.coins.append(pb.SearchCoin(
                id=c.get("id", ""),
                name=c.get("name", ""),
                symbol=c.get("symbol", ""),
                market_cap_rank=c.get("market_cap_rank") or 0,
                thumb=c.get("thumb", ""),
                large=c.get("large", ""),
            ))
        for e in raw.get("exchanges", []):
            resp.exchanges.append(pb.SearchExchange(
                id=e.get("id", ""),
                name=e.get("name", ""),
                market_type=e.get("market_type", ""),
                thumb=e.get("thumb", ""),
            ))
        for cat in raw.get("categories", []):
            resp.categories.append(pb.SearchCategory(
                id=str(cat.get("id", "")),
                name=cat.get("name", ""),
            ))
        return resp

    def GetTrending(self, request: Any, context: Any = None) -> pb.GetTrendingResponse:
        raw = self._get("/search/trending")
        resp = pb.GetTrendingResponse()
        for item in raw.get("coins", []):
            c = item.get("item", {})
            resp.coins.append(pb.TrendingCoin(
                id=c.get("id", ""),
                name=c.get("name", ""),
                symbol=c.get("symbol", ""),
                market_cap_rank=c.get("market_cap_rank") or 0,
                thumb=c.get("thumb", ""),
                price_btc=c.get("price_btc", 0),
                score=c.get("score", 0),
            ))
        for item in raw.get("nfts", []):
            resp.nfts.append(pb.TrendingNFT(
                id=item.get("id", ""),
                name=item.get("name", ""),
                symbol=item.get("symbol", ""),
                thumb=item.get("thumb", ""),
            ))
        for item in raw.get("categories", []):
            resp.categories.append(pb.TrendingCategory(
                id=str(item.get("id", "")),
                name=item.get("name", ""),
                coins_count=item.get("coins_count", 0),
            ))
        return resp

    def GetMarkets(self, request: Any, context: Any = None) -> pb.GetMarketsResponse:
        params = {
            "vs_currency": request.vs_currency or "usd",
            "order": request.order or "market_cap_desc",
            "per_page": request.per_page or 100,
            "page": request.page or 1,
        }
        if request.category:
            params["category"] = request.category

        raw = self._get("/coins/markets", params)
        resp = pb.GetMarketsResponse()
        for c in raw:
            resp.coins.append(pb.CoinMarket(
                id=c.get("id", ""),
                symbol=c.get("symbol", ""),
                name=c.get("name", ""),
                image=c.get("image", ""),
                current_price=c.get("current_price") or 0,
                market_cap=c.get("market_cap") or 0,
                market_cap_rank=c.get("market_cap_rank") or 0,
                total_volume=c.get("total_volume") or 0,
                high_24h=c.get("high_24h") or 0,
                low_24h=c.get("low_24h") or 0,
                price_change_24h=c.get("price_change_24h") or 0,
                price_change_percentage_24h=c.get("price_change_percentage_24h") or 0,
                circulating_supply=c.get("circulating_supply") or 0,
                total_supply=c.get("total_supply") or 0,
                max_supply=c.get("max_supply") or 0,
                ath=c.get("ath") or 0,
                ath_change_percentage=c.get("ath_change_percentage") or 0,
                ath_date=str(c.get("ath_date", "")),
                atl=c.get("atl") or 0,
                atl_change_percentage=c.get("atl_change_percentage") or 0,
                atl_date=str(c.get("atl_date", "")),
                last_updated=str(c.get("last_updated", "")),
            ))
        return resp

    def GetCoin(self, request: Any, context: Any = None) -> pb.GetCoinResponse:
        raw = self._get(f"/coins/{request.coin_id}", params={
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "false",
        })
        md = raw.get("market_data", {})
        desc = raw.get("description", {})
        links = raw.get("links", {})
        homepages = links.get("homepage", [])
        explorers = links.get("blockchain_site", [])

        return pb.GetCoinResponse(
            id=raw.get("id", ""),
            symbol=raw.get("symbol", ""),
            name=raw.get("name", ""),
            description=desc.get("en", ""),
            image=(raw.get("image", {}) or {}).get("large", ""),
            market_cap_rank=raw.get("market_cap_rank") or 0,
            current_price_usd=(md.get("current_price") or {}).get("usd", 0),
            market_cap_usd=(md.get("market_cap") or {}).get("usd", 0),
            total_volume_usd=(md.get("total_volume") or {}).get("usd", 0),
            high_24h_usd=(md.get("high_24h") or {}).get("usd", 0),
            low_24h_usd=(md.get("low_24h") or {}).get("usd", 0),
            price_change_percentage_24h=md.get("price_change_percentage_24h") or 0,
            price_change_percentage_7d=md.get("price_change_percentage_7d") or 0,
            price_change_percentage_30d=md.get("price_change_percentage_30d") or 0,
            circulating_supply=md.get("circulating_supply") or 0,
            total_supply=md.get("total_supply") or 0,
            max_supply=md.get("max_supply") or 0,
            ath_usd=(md.get("ath") or {}).get("usd", 0),
            ath_change_percentage=(md.get("ath_change_percentage") or {}).get("usd", 0),
            ath_date=str((md.get("ath_date") or {}).get("usd", "")),
            genesis_date=str(raw.get("genesis_date") or ""),
            homepage=homepages[0] if homepages else "",
            blockchain_site=next((s for s in explorers if s), ""),
            subreddit_url=links.get("subreddit_url", "") or "",
            categories=raw.get("categories", []) or [],
            sentiment_votes_up_percentage=raw.get("sentiment_votes_up_percentage") or 0,
            watchlist_users=raw.get("watchlist_portfolio_users") or 0,
        )

    def GetMarketChart(self, request: Any, context: Any = None) -> pb.GetMarketChartResponse:
        raw = self._get(f"/coins/{request.coin_id}/market_chart", params={
            "vs_currency": request.vs_currency or "usd",
            "days": request.days or "7",
        })
        resp = pb.GetMarketChartResponse()
        for ts, val in raw.get("prices", []):
            resp.prices.append(pb.TimestampValue(timestamp=int(ts), value=val))
        for ts, val in raw.get("market_caps", []):
            resp.market_caps.append(pb.TimestampValue(timestamp=int(ts), value=val))
        for ts, val in raw.get("total_volumes", []):
            resp.total_volumes.append(pb.TimestampValue(timestamp=int(ts), value=val))
        return resp

    def GetOHLC(self, request: Any, context: Any = None) -> pb.GetOHLCResponse:
        raw = self._get(f"/coins/{request.coin_id}/ohlc", params={
            "vs_currency": request.vs_currency or "usd",
            "days": request.days or "7",
        })
        resp = pb.GetOHLCResponse()
        for candle in raw:
            resp.candles.append(pb.OHLC(
                timestamp=int(candle[0]),
                open=candle[1],
                high=candle[2],
                low=candle[3],
                close=candle[4],
            ))
        return resp

    def GetGlobal(self, request: Any, context: Any = None) -> pb.GetGlobalResponse:
        raw = self._get("/global")
        data = raw.get("data", {})
        mcp = data.get("market_cap_percentage", {})
        return pb.GetGlobalResponse(
            active_cryptocurrencies=data.get("active_cryptocurrencies", 0),
            markets=data.get("markets", 0),
            total_market_cap_usd=(data.get("total_market_cap") or {}).get("usd", 0),
            total_volume_usd=(data.get("total_volume") or {}).get("usd", 0),
            btc_dominance=mcp.get("btc", 0),
            eth_dominance=mcp.get("eth", 0),
            market_cap_change_percentage_24h=data.get("market_cap_change_percentage_24h_usd", 0),
            updated_at=data.get("updated_at", 0),
        )

    def GetCategories(self, request: Any, context: Any = None) -> pb.GetCategoriesResponse:
        raw = self._get("/coins/categories", params={
            "order": request.order or "market_cap_desc",
        })
        resp = pb.GetCategoriesResponse()
        for cat in raw:
            resp.categories.append(pb.Category(
                id=str(cat.get("id", "")),
                name=cat.get("name", ""),
                market_cap=cat.get("market_cap") or 0,
                market_cap_change_24h=cat.get("market_cap_change_24h") or 0,
                volume_24h=cat.get("volume_24h") or 0,
                top_3_coins=cat.get("top_3_coins", []) or [],
                updated_at=str(cat.get("updated_at", "")),
            ))
        return resp

    def GetExchangeRates(self, request: Any, context: Any = None) -> pb.GetExchangeRatesResponse:
        raw = self._get("/exchange_rates")
        resp = pb.GetExchangeRatesResponse()
        for code, data in raw.get("rates", {}).items():
            resp.rates[code].CopyFrom(pb.ExchangeRate(
                name=data.get("name", ""),
                unit=data.get("unit", ""),
                value=data.get("value", 0),
                type=data.get("type", ""),
            ))
        return resp
