"""AlphaVantageService — wraps the Alpha Vantage API into proto RPCs."""

from __future__ import annotations

import os
from typing import Any

import httpx

from alphavantage_mcp.gen.alphavantage.v1 import alphavantage_pb2 as pb

_BASE_URL = "https://www.alphavantage.co"

# Alpha Vantage interval param values for technical indicators.
_INTERVAL_MAP = {
    "daily": "daily",
    "weekly": "weekly",
    "monthly": "monthly",
}


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Convert a value to float, returning default if it's None or 'None'."""
    if val is None or val == "None" or val == "-":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    """Convert a value to int, returning default if it's None or 'None'."""
    if val is None or val == "None" or val == "-":
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


class AlphaVantageService:
    """Implements AlphaVantageService RPCs via the Alpha Vantage API."""

    def __init__(self, *, api_key: str | None = None):
        self._http = httpx.Client(timeout=30)
        self._api_key = api_key or os.environ.get("ALPHA_VANTAGE_API_KEY", "demo")

    def _get(self, function: str, **params: Any) -> Any:
        params["function"] = function
        params["apikey"] = self._api_key
        resp = self._http.get(f"{_BASE_URL}/query", params=params)
        resp.raise_for_status()
        return resp.json()

    # --- RPCs ---

    def GetQuote(self, request: Any, context: Any = None) -> pb.GetQuoteResponse:
        raw = self._get("GLOBAL_QUOTE", symbol=request.symbol)
        quote = raw.get("Global Quote", {})
        return pb.GetQuoteResponse(
            symbol=quote.get("01. symbol", ""),
            open=_safe_float(quote.get("02. open")),
            high=_safe_float(quote.get("03. high")),
            low=_safe_float(quote.get("04. low")),
            price=_safe_float(quote.get("05. price")),
            volume=_safe_int(quote.get("06. volume")),
            latest_trading_day=quote.get("07. latest trading day", ""),
            previous_close=_safe_float(quote.get("08. previous close")),
            change=_safe_float(quote.get("09. change")),
            change_percent=quote.get("10. change percent", ""),
        )

    def SearchSymbol(self, request: Any, context: Any = None) -> pb.SearchSymbolResponse:
        raw = self._get("SYMBOL_SEARCH", keywords=request.keywords)
        resp = pb.SearchSymbolResponse()
        for m in raw.get("bestMatches", []):
            resp.matches.append(pb.SymbolMatch(
                symbol=m.get("1. symbol", ""),
                name=m.get("2. name", ""),
                type=m.get("3. type", ""),
                region=m.get("4. region", ""),
                market_open=m.get("5. marketOpen", ""),
                market_close=m.get("6. marketClose", ""),
                timezone=m.get("7. timezone", ""),
                currency=m.get("8. currency", ""),
                match_score=_safe_float(m.get("9. matchScore")),
            ))
        return resp

    def _parse_time_series(self, raw: dict, ts_key: str, meta_key: str = "Meta Data") -> pb.GetTimeSeriesResponse:
        meta = raw.get(meta_key, {})
        # Meta data keys vary: "2. Symbol" in daily, "2. Symbol" in weekly/monthly.
        symbol = ""
        last_refreshed = ""
        for k, v in meta.items():
            if "symbol" in k.lower():
                symbol = v
            if "last refreshed" in k.lower():
                last_refreshed = v

        resp = pb.GetTimeSeriesResponse(
            symbol=symbol,
            last_refreshed=last_refreshed,
        )
        ts_data = raw.get(ts_key, {})
        for date_str, ohlcv in sorted(ts_data.items(), reverse=True):
            resp.entries.append(pb.TimeSeriesEntry(
                date=date_str,
                open=_safe_float(ohlcv.get("1. open")),
                high=_safe_float(ohlcv.get("2. high")),
                low=_safe_float(ohlcv.get("3. low")),
                close=_safe_float(ohlcv.get("4. close")),
                volume=_safe_int(ohlcv.get("5. volume")),
            ))
        return resp

    def GetDailyTimeSeries(self, request: Any, context: Any = None) -> pb.GetTimeSeriesResponse:
        params = {"symbol": request.symbol}
        if request.outputsize:
            params["outputsize"] = request.outputsize
        raw = self._get("TIME_SERIES_DAILY", **params)
        return self._parse_time_series(raw, "Time Series (Daily)")

    def GetWeeklyTimeSeries(self, request: Any, context: Any = None) -> pb.GetTimeSeriesResponse:
        raw = self._get("TIME_SERIES_WEEKLY", symbol=request.symbol)
        return self._parse_time_series(raw, "Weekly Time Series")

    def GetMonthlyTimeSeries(self, request: Any, context: Any = None) -> pb.GetTimeSeriesResponse:
        raw = self._get("TIME_SERIES_MONTHLY", symbol=request.symbol)
        return self._parse_time_series(raw, "Monthly Time Series")

    def _parse_indicator(self, raw: dict, indicator_key: str, value_key: str) -> pb.GetIndicatorResponse:
        meta = raw.get("Meta Data", {})
        symbol = ""
        indicator = ""
        for k, v in meta.items():
            if "symbol" in k.lower():
                symbol = v
            if "indicator" in k.lower():
                indicator = v

        resp = pb.GetIndicatorResponse(
            symbol=symbol,
            indicator=indicator,
        )
        ta_data = raw.get(indicator_key, {})
        for date_str, vals in sorted(ta_data.items(), reverse=True):
            resp.entries.append(pb.IndicatorEntry(
                date=date_str,
                value=_safe_float(vals.get(value_key)),
            ))
        return resp

    def GetSMA(self, request: Any, context: Any = None) -> pb.GetIndicatorResponse:
        interval = _INTERVAL_MAP.get(request.interval or "daily", "daily")
        raw = self._get(
            "SMA",
            symbol=request.symbol,
            interval=interval,
            time_period=request.time_period or 20,
            series_type=request.series_type or "close",
        )
        return self._parse_indicator(raw, "Technical Analysis: SMA", "SMA")

    def GetRSI(self, request: Any, context: Any = None) -> pb.GetIndicatorResponse:
        interval = _INTERVAL_MAP.get(request.interval or "daily", "daily")
        raw = self._get(
            "RSI",
            symbol=request.symbol,
            interval=interval,
            time_period=request.time_period or 14,
            series_type=request.series_type or "close",
        )
        return self._parse_indicator(raw, "Technical Analysis: RSI", "RSI")

    def GetMACD(self, request: Any, context: Any = None) -> pb.GetMACDResponse:
        interval = _INTERVAL_MAP.get(request.interval or "daily", "daily")
        params = {
            "symbol": request.symbol,
            "interval": interval,
            "series_type": request.series_type or "close",
        }
        if request.fast_period:
            params["fastperiod"] = request.fast_period
        if request.slow_period:
            params["slowperiod"] = request.slow_period
        if request.signal_period:
            params["signalperiod"] = request.signal_period

        raw = self._get("MACD", **params)

        meta = raw.get("Meta Data", {})
        symbol = ""
        for k, v in meta.items():
            if "symbol" in k.lower():
                symbol = v

        resp = pb.GetMACDResponse(symbol=symbol)
        ta_data = raw.get("Technical Analysis: MACD", {})
        for date_str, vals in sorted(ta_data.items(), reverse=True):
            resp.entries.append(pb.MACDEntry(
                date=date_str,
                macd=_safe_float(vals.get("MACD")),
                signal=_safe_float(vals.get("MACD_Signal")),
                histogram=_safe_float(vals.get("MACD_Hist")),
            ))
        return resp

    def GetCompanyOverview(self, request: Any, context: Any = None) -> pb.GetCompanyOverviewResponse:
        raw = self._get("OVERVIEW", symbol=request.symbol)
        return pb.GetCompanyOverviewResponse(
            symbol=raw.get("Symbol", ""),
            name=raw.get("Name", ""),
            description=raw.get("Description", ""),
            exchange=raw.get("Exchange", ""),
            currency=raw.get("Currency", ""),
            country=raw.get("Country", ""),
            sector=raw.get("Sector", ""),
            industry=raw.get("Industry", ""),
            market_capitalization=_safe_float(raw.get("MarketCapitalization")),
            pe_ratio=_safe_float(raw.get("PERatio")),
            peg_ratio=_safe_float(raw.get("PEGRatio")),
            book_value=_safe_float(raw.get("BookValue")),
            eps=_safe_float(raw.get("EPS")),
            revenue_per_share=_safe_float(raw.get("RevenuePerShareTTM")),
            profit_margin=_safe_float(raw.get("ProfitMargin")),
            dividend_per_share=_safe_float(raw.get("DividendPerShare")),
            dividend_yield=_safe_float(raw.get("DividendYield")),
            week_high_52=_safe_float(raw.get("52WeekHigh")),
            week_low_52=_safe_float(raw.get("52WeekLow")),
            moving_average_50=_safe_float(raw.get("50DayMovingAverage")),
            moving_average_200=_safe_float(raw.get("200DayMovingAverage")),
            shares_outstanding=_safe_int(raw.get("SharesOutstanding")),
            price_to_book_ratio=_safe_float(raw.get("PriceToBookRatio")),
            beta=_safe_float(raw.get("Beta")),
            analyst_target_price=_safe_float(raw.get("AnalystTargetPrice")),
            forward_pe=_safe_float(raw.get("ForwardPE")),
        )

    def GetEarnings(self, request: Any, context: Any = None) -> pb.GetEarningsResponse:
        raw = self._get("EARNINGS", symbol=request.symbol)
        resp = pb.GetEarningsResponse(
            symbol=raw.get("symbol", request.symbol),
        )
        for ae in raw.get("annualEarnings", []):
            resp.annual_earnings.append(pb.AnnualEarnings(
                fiscal_date_ending=ae.get("fiscalDateEnding", ""),
                reported_eps=_safe_float(ae.get("reportedEPS")),
            ))
        for qe in raw.get("quarterlyEarnings", []):
            resp.quarterly_earnings.append(pb.QuarterlyEarnings(
                fiscal_date_ending=qe.get("fiscalDateEnding", ""),
                reported_eps=_safe_float(qe.get("reportedEPS")),
                estimated_eps=_safe_float(qe.get("estimatedEPS")),
                surprise=_safe_float(qe.get("surprise")),
                surprise_percentage=_safe_float(qe.get("surprisePercentage")),
                reported_date=qe.get("reportedDate", ""),
            ))
        return resp
