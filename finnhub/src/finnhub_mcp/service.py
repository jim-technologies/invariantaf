"""FinnhubService — wraps the Finnhub API into proto RPCs."""

from __future__ import annotations

import os
from typing import Any

import httpx

from finnhub_mcp.gen.finnhub.v1 import finnhub_pb2 as pb

_BASE_URL = "https://finnhub.io/api/v1"


class FinnhubService:
    """Implements FinnhubService RPCs via the Finnhub REST API."""

    def __init__(self, *, api_key: str | None = None):
        self._http = httpx.Client(timeout=30)
        self._api_key = api_key or os.environ.get("FINNHUB_API_KEY", "")

    def _get(self, path: str, **params: Any) -> Any:
        params["token"] = self._api_key
        resp = self._http.get(f"{_BASE_URL}/{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def GetQuote(self, request: Any, context: Any = None) -> pb.GetQuoteResponse:
        raw = self._get("quote", symbol=request.symbol)
        return pb.GetQuoteResponse(
            current_price=raw.get("c", 0),
            change=raw.get("d", 0),
            percent_change=raw.get("dp", 0),
            high=raw.get("h", 0),
            low=raw.get("l", 0),
            open=raw.get("o", 0),
            previous_close=raw.get("pc", 0),
            timestamp=raw.get("t", 0),
        )

    def SearchSymbol(self, request: Any, context: Any = None) -> pb.SearchSymbolResponse:
        raw = self._get("search", q=request.query)
        resp = pb.SearchSymbolResponse(count=raw.get("count", 0))
        for r in raw.get("result", []):
            resp.results.append(pb.SymbolMatch(
                symbol=r.get("symbol", ""),
                description=r.get("description", ""),
                display_symbol=r.get("displaySymbol", ""),
                type=r.get("type", ""),
            ))
        return resp

    def GetCompanyProfile(self, request: Any, context: Any = None) -> pb.GetCompanyProfileResponse:
        raw = self._get("stock/profile2", symbol=request.symbol)
        return pb.GetCompanyProfileResponse(
            ticker=raw.get("ticker", ""),
            name=raw.get("name", ""),
            country=raw.get("country", ""),
            currency=raw.get("currency", ""),
            exchange=raw.get("exchange", ""),
            finnhub_industry=raw.get("finnhubIndustry", ""),
            ipo=raw.get("ipo", ""),
            logo=raw.get("logo", ""),
            market_capitalization=raw.get("marketCapitalization", 0),
            share_outstanding=raw.get("shareOutstanding", 0),
            weburl=raw.get("weburl", ""),
            phone=raw.get("phone", ""),
        )

    def GetCompanyNews(self, request: Any, context: Any = None) -> pb.GetCompanyNewsResponse:
        params = {"symbol": request.symbol}
        if request.from_date:
            params["from"] = request.from_date
        if request.to_date:
            params["to"] = request.to_date
        raw = self._get("company-news", **params)
        resp = pb.GetCompanyNewsResponse()
        for a in raw:
            resp.articles.append(pb.NewsArticle(
                headline=a.get("headline", ""),
                summary=a.get("summary", ""),
                source=a.get("source", ""),
                url=a.get("url", ""),
                datetime=a.get("datetime", 0),
                related=a.get("related", ""),
                category=a.get("category", ""),
                image=a.get("image", ""),
                id=a.get("id", 0),
            ))
        return resp

    def GetEarningsCalendar(self, request: Any, context: Any = None) -> pb.GetEarningsCalendarResponse:
        params = {}
        if request.from_date:
            params["from"] = request.from_date
        if request.to_date:
            params["to"] = request.to_date
        raw = self._get("calendar/earnings", **params)
        resp = pb.GetEarningsCalendarResponse()
        for e in raw.get("earningsCalendar", []):
            resp.earnings.append(pb.EarningsEntry(
                symbol=e.get("symbol", ""),
                date=e.get("date", ""),
                hour=e.get("hour", ""),
                quarter=e.get("quarter", 0),
                year=e.get("year", 0),
                eps_estimate=e.get("epsEstimate") or 0,
                eps_actual=e.get("epsActual") or 0,
                revenue_estimate=e.get("revenueEstimate") or 0,
                revenue_actual=e.get("revenueActual") or 0,
            ))
        return resp

    def GetRecommendationTrends(self, request: Any, context: Any = None) -> pb.GetRecommendationTrendsResponse:
        raw = self._get("stock/recommendation", symbol=request.symbol)
        resp = pb.GetRecommendationTrendsResponse()
        for r in raw:
            resp.trends.append(pb.RecommendationTrend(
                period=r.get("period", ""),
                strong_buy=r.get("strongBuy", 0),
                buy=r.get("buy", 0),
                hold=r.get("hold", 0),
                sell=r.get("sell", 0),
                strong_sell=r.get("strongSell", 0),
            ))
        return resp

    def GetInsiderTransactions(self, request: Any, context: Any = None) -> pb.GetInsiderTransactionsResponse:
        raw = self._get("stock/insider-transactions", symbol=request.symbol)
        resp = pb.GetInsiderTransactionsResponse()
        for t in raw.get("data", []):
            resp.transactions.append(pb.InsiderTransaction(
                name=t.get("name", ""),
                share=t.get("share", 0),
                change=t.get("change", 0),
                filing_date=t.get("filingDate", ""),
                transaction_date=t.get("transactionDate", ""),
                transaction_code=t.get("transactionCode", ""),
                transaction_price=t.get("transactionPrice") or 0,
            ))
        return resp

    def GetMarketNews(self, request: Any, context: Any = None) -> pb.GetMarketNewsResponse:
        params = {"category": request.category or "general"}
        if request.min_id:
            params["minId"] = request.min_id
        raw = self._get("news", **params)
        resp = pb.GetMarketNewsResponse()
        for a in raw:
            resp.articles.append(pb.NewsArticle(
                headline=a.get("headline", ""),
                summary=a.get("summary", ""),
                source=a.get("source", ""),
                url=a.get("url", ""),
                datetime=a.get("datetime", 0),
                related=a.get("related", ""),
                category=a.get("category", ""),
                image=a.get("image", ""),
                id=a.get("id", 0),
            ))
        return resp

    def GetPeers(self, request: Any, context: Any = None) -> pb.GetPeersResponse:
        raw = self._get("stock/peers", symbol=request.symbol)
        return pb.GetPeersResponse(peers=raw if isinstance(raw, list) else [])

    def GetBasicFinancials(self, request: Any, context: Any = None) -> pb.GetBasicFinancialsResponse:
        raw = self._get("stock/metric", symbol=request.symbol, metric=request.metric or "all")
        m = raw.get("metric", {})
        return pb.GetBasicFinancialsResponse(
            pe_trailing=m.get("peTTM") or 0,
            pb_quarterly=m.get("pbQuarterly") or 0,
            eps_trailing=m.get("epsTTM") or 0,
            dividend_yield_indicated=m.get("dividendYieldIndicatedAnnual") or 0,
            week_52_high=m.get("52WeekHigh") or 0,
            week_52_low=m.get("52WeekLow") or 0,
            roe_trailing=m.get("roeTTM") or 0,
            total_debt_to_equity_quarterly=m.get("totalDebt/totalEquityQuarterly") or 0,
            net_profit_margin_trailing=m.get("netProfitMarginTTM") or 0,
            gross_margin_trailing=m.get("grossMarginTTM") or 0,
            operating_margin_trailing=m.get("operatingMarginTTM") or 0,
            beta=m.get("beta") or 0,
            ten_day_average_volume=m.get("10DayAverageTradingVolume") or 0,
            revenue_growth_quarterly_yoy=m.get("revenueGrowthQuarterlyYoy") or 0,
            market_capitalization=m.get("marketCapitalization") or 0,
        )
