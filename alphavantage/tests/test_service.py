"""Unit tests — every AlphaVantageService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from alphavantage_mcp.gen.alphavantage.v1 import alphavantage_pb2 as pb
from tests.conftest import (
    FAKE_COMPANY_OVERVIEW,
    FAKE_DAILY_TIME_SERIES,
    FAKE_EARNINGS,
    FAKE_GLOBAL_QUOTE,
    FAKE_MACD,
    FAKE_MONTHLY_TIME_SERIES,
    FAKE_RSI,
    FAKE_SMA,
    FAKE_SYMBOL_SEARCH,
    FAKE_WEEKLY_TIME_SERIES,
)


class TestGetQuote:
    def test_returns_quote(self, service):
        resp = service.GetQuote(pb.GetQuoteRequest(symbol="AAPL"))
        assert resp.symbol == "AAPL"
        assert resp.price == 183.58
        assert resp.change == 2.4
        assert resp.change_percent == "1.3244%"
        assert resp.volume == 48425673
        assert resp.latest_trading_day == "2025-01-15"

    def test_previous_close(self, service):
        resp = service.GetQuote(pb.GetQuoteRequest(symbol="AAPL"))
        assert resp.previous_close == 181.18
        assert resp.open == 182.35
        assert resp.high == 183.92
        assert resp.low == 181.46

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetQuote(pb.GetQuoteRequest(symbol="NONEXISTENT"))
        assert resp.symbol == ""
        assert resp.price == 0.0


class TestSearchSymbol:
    def test_returns_matches(self, service):
        resp = service.SearchSymbol(pb.SearchSymbolRequest(keywords="Apple"))
        assert len(resp.matches) == 2
        assert resp.matches[0].symbol == "AAPL"
        assert resp.matches[0].name == "Apple Inc"
        assert resp.matches[0].type == "Equity"
        assert resp.matches[0].region == "United States"

    def test_match_score(self, service):
        resp = service.SearchSymbol(pb.SearchSymbolRequest(keywords="Apple"))
        assert resp.matches[0].match_score == 1.0
        assert resp.matches[1].match_score == 0.8

    def test_market_info(self, service):
        resp = service.SearchSymbol(pb.SearchSymbolRequest(keywords="Apple"))
        m = resp.matches[0]
        assert m.market_open == "09:30"
        assert m.market_close == "16:00"
        assert m.timezone == "UTC-04"
        assert m.currency == "USD"

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.SearchSymbol(pb.SearchSymbolRequest(keywords="zzzzz"))
        assert len(resp.matches) == 0


class TestGetDailyTimeSeries:
    def test_returns_entries(self, service):
        resp = service.GetDailyTimeSeries(pb.GetDailyTimeSeriesRequest(symbol="AAPL"))
        assert resp.symbol == "AAPL"
        assert resp.last_refreshed == "2025-01-15"
        assert len(resp.entries) == 2

    def test_entry_fields(self, service):
        resp = service.GetDailyTimeSeries(pb.GetDailyTimeSeriesRequest(symbol="AAPL"))
        # Most recent first (sorted reverse).
        entry = resp.entries[0]
        assert entry.date == "2025-01-15"
        assert entry.open == 182.35
        assert entry.high == 183.92
        assert entry.low == 181.46
        assert entry.close == 183.58
        assert entry.volume == 48425673

    def test_sorted_descending(self, service):
        resp = service.GetDailyTimeSeries(pb.GetDailyTimeSeriesRequest(symbol="AAPL"))
        assert resp.entries[0].date > resp.entries[1].date


class TestGetWeeklyTimeSeries:
    def test_returns_entries(self, service):
        resp = service.GetWeeklyTimeSeries(pb.GetWeeklyTimeSeriesRequest(symbol="AAPL"))
        assert resp.symbol == "AAPL"
        assert len(resp.entries) == 2

    def test_entry_fields(self, service):
        resp = service.GetWeeklyTimeSeries(pb.GetWeeklyTimeSeriesRequest(symbol="AAPL"))
        entry = resp.entries[0]
        assert entry.date == "2025-01-15"
        assert entry.open == 180.0
        assert entry.high == 185.0
        assert entry.volume == 200000000


class TestGetMonthlyTimeSeries:
    def test_returns_entries(self, service):
        resp = service.GetMonthlyTimeSeries(pb.GetMonthlyTimeSeriesRequest(symbol="AAPL"))
        assert resp.symbol == "AAPL"
        assert len(resp.entries) == 2

    def test_entry_fields(self, service):
        resp = service.GetMonthlyTimeSeries(pb.GetMonthlyTimeSeriesRequest(symbol="AAPL"))
        entry = resp.entries[0]
        assert entry.date == "2025-01-15"
        assert entry.open == 175.0
        assert entry.close == 183.58
        assert entry.volume == 800000000


class TestGetSMA:
    def test_returns_entries(self, service):
        resp = service.GetSMA(pb.GetSMARequest(symbol="AAPL"))
        assert resp.symbol == "AAPL"
        assert "SMA" in resp.indicator
        assert len(resp.entries) == 3

    def test_entry_values(self, service):
        resp = service.GetSMA(pb.GetSMARequest(symbol="AAPL"))
        # Most recent first.
        assert resp.entries[0].date == "2025-01-15"
        assert resp.entries[0].value == 180.25

    def test_sorted_descending(self, service):
        resp = service.GetSMA(pb.GetSMARequest(symbol="AAPL"))
        assert resp.entries[0].date > resp.entries[1].date


class TestGetRSI:
    def test_returns_entries(self, service):
        resp = service.GetRSI(pb.GetRSIRequest(symbol="AAPL"))
        assert resp.symbol == "AAPL"
        assert "RSI" in resp.indicator
        assert len(resp.entries) == 3

    def test_entry_values(self, service):
        resp = service.GetRSI(pb.GetRSIRequest(symbol="AAPL"))
        assert resp.entries[0].date == "2025-01-15"
        assert resp.entries[0].value == 62.34

    def test_rsi_range(self, service):
        resp = service.GetRSI(pb.GetRSIRequest(symbol="AAPL"))
        for entry in resp.entries:
            assert 0 <= entry.value <= 100


class TestGetMACD:
    def test_returns_entries(self, service):
        resp = service.GetMACD(pb.GetMACDRequest(symbol="AAPL"))
        assert resp.symbol == "AAPL"
        assert len(resp.entries) == 2

    def test_entry_values(self, service):
        resp = service.GetMACD(pb.GetMACDRequest(symbol="AAPL"))
        entry = resp.entries[0]
        assert entry.date == "2025-01-15"
        assert entry.macd == 1.2345
        assert entry.signal == 0.9876
        assert entry.histogram == 0.2469

    def test_histogram_is_macd_minus_signal(self, service):
        resp = service.GetMACD(pb.GetMACDRequest(symbol="AAPL"))
        entry = resp.entries[0]
        assert abs(entry.histogram - (entry.macd - entry.signal)) < 0.001


class TestGetCompanyOverview:
    def test_basic_fields(self, service):
        resp = service.GetCompanyOverview(pb.GetCompanyOverviewRequest(symbol="AAPL"))
        assert resp.symbol == "AAPL"
        assert resp.name == "Apple Inc"
        assert resp.exchange == "NASDAQ"
        assert resp.currency == "USD"
        assert resp.country == "USA"
        assert resp.sector == "TECHNOLOGY"
        assert resp.industry == "ELECTRONIC COMPUTERS"

    def test_description(self, service):
        resp = service.GetCompanyOverview(pb.GetCompanyOverviewRequest(symbol="AAPL"))
        assert "Apple" in resp.description
        assert "smartphones" in resp.description

    def test_valuation_metrics(self, service):
        resp = service.GetCompanyOverview(pb.GetCompanyOverviewRequest(symbol="AAPL"))
        assert resp.market_capitalization == 2850000000000
        assert resp.pe_ratio == 29.50
        assert resp.peg_ratio == 2.15
        assert resp.eps == 6.42
        assert resp.forward_pe == 28.10

    def test_price_metrics(self, service):
        resp = service.GetCompanyOverview(pb.GetCompanyOverviewRequest(symbol="AAPL"))
        assert resp.week_high_52 == 199.62
        assert resp.week_low_52 == 164.08
        assert resp.moving_average_50 == 185.23
        assert resp.moving_average_200 == 181.45

    def test_dividend_and_shares(self, service):
        resp = service.GetCompanyOverview(pb.GetCompanyOverviewRequest(symbol="AAPL"))
        assert resp.dividend_per_share == 0.96
        assert resp.dividend_yield == 0.0052
        assert resp.shares_outstanding == 15115000000
        assert resp.beta == 1.24

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetCompanyOverview(pb.GetCompanyOverviewRequest(symbol="NONEXIST"))
        assert resp.symbol == ""
        assert resp.market_capitalization == 0.0


class TestGetEarnings:
    def test_returns_symbol(self, service):
        resp = service.GetEarnings(pb.GetEarningsRequest(symbol="AAPL"))
        assert resp.symbol == "AAPL"

    def test_annual_earnings(self, service):
        resp = service.GetEarnings(pb.GetEarningsRequest(symbol="AAPL"))
        assert len(resp.annual_earnings) == 2
        assert resp.annual_earnings[0].fiscal_date_ending == "2024-09-30"
        assert resp.annual_earnings[0].reported_eps == 6.42
        assert resp.annual_earnings[1].reported_eps == 6.13

    def test_quarterly_earnings(self, service):
        resp = service.GetEarnings(pb.GetEarningsRequest(symbol="AAPL"))
        assert len(resp.quarterly_earnings) == 2
        qe = resp.quarterly_earnings[0]
        assert qe.fiscal_date_ending == "2024-09-30"
        assert qe.reported_eps == 1.64
        assert qe.estimated_eps == 1.60
        assert qe.surprise == 0.04
        assert qe.surprise_percentage == 2.5
        assert qe.reported_date == "2024-10-31"

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetEarnings(pb.GetEarningsRequest(symbol="NONEXIST"))
        assert len(resp.annual_earnings) == 0
        assert len(resp.quarterly_earnings) == 0
