"""Unit tests — every FinnhubService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from finnhub_mcp.gen.finnhub.v1 import finnhub_pb2 as pb
from tests.conftest import (
    FAKE_BASIC_FINANCIALS,
    FAKE_COMPANY_NEWS,
    FAKE_COMPANY_PROFILE,
    FAKE_EARNINGS,
    FAKE_INSIDER_TRANSACTIONS,
    FAKE_MARKET_NEWS,
    FAKE_PEERS,
    FAKE_QUOTE,
    FAKE_RECOMMENDATION,
    FAKE_SEARCH,
)


class TestGetQuote:
    def test_returns_quote(self, service):
        resp = service.GetQuote(pb.GetQuoteRequest(symbol="AAPL"))
        assert resp.current_price == 178.72
        assert resp.change == 2.38
        assert resp.percent_change == 1.35
        assert resp.high == 179.63
        assert resp.low == 176.21
        assert resp.open == 176.50
        assert resp.previous_close == 176.34
        assert resp.timestamp == 1700000000

    def test_passes_symbol(self, service, mock_http):
        service.GetQuote(pb.GetQuoteRequest(symbol="TSLA"))
        call_args = mock_http.get.call_args
        assert "TSLA" in str(call_args)

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={})
        )
        resp = service.GetQuote(pb.GetQuoteRequest(symbol="UNKNOWN"))
        assert resp.current_price == 0
        assert resp.timestamp == 0


class TestSearchSymbol:
    def test_returns_results(self, service):
        resp = service.SearchSymbol(pb.SearchSymbolRequest(query="apple"))
        assert resp.count == 2
        assert len(resp.results) == 2
        assert resp.results[0].symbol == "AAPL"
        assert resp.results[0].description == "Apple Inc"
        assert resp.results[0].type == "Common Stock"

    def test_second_result(self, service):
        resp = service.SearchSymbol(pb.SearchSymbolRequest(query="apple"))
        assert resp.results[1].symbol == "AAPL.SW"
        assert resp.results[1].display_symbol == "AAPL.SW"


class TestGetCompanyProfile:
    def test_basic_fields(self, service):
        resp = service.GetCompanyProfile(pb.GetCompanyProfileRequest(symbol="AAPL"))
        assert resp.ticker == "AAPL"
        assert resp.name == "Apple Inc"
        assert resp.country == "US"
        assert resp.currency == "USD"

    def test_exchange_and_industry(self, service):
        resp = service.GetCompanyProfile(pb.GetCompanyProfileRequest(symbol="AAPL"))
        assert "NASDAQ" in resp.exchange
        assert resp.finnhub_industry == "Technology"

    def test_financial_fields(self, service):
        resp = service.GetCompanyProfile(pb.GetCompanyProfileRequest(symbol="AAPL"))
        assert resp.market_capitalization == 2800000
        assert resp.share_outstanding == 15550.0

    def test_metadata_fields(self, service):
        resp = service.GetCompanyProfile(pb.GetCompanyProfileRequest(symbol="AAPL"))
        assert resp.ipo == "1980-12-12"
        assert "apple.com" in resp.weburl
        assert resp.logo != ""


class TestGetCompanyNews:
    def test_returns_articles(self, service):
        resp = service.GetCompanyNews(pb.GetCompanyNewsRequest(
            symbol="AAPL", from_date="2024-01-01", to_date="2024-12-31",
        ))
        assert len(resp.articles) == 2
        assert resp.articles[0].headline == "Apple Unveils New iPhone"
        assert resp.articles[0].source == "Reuters"

    def test_article_fields(self, service):
        resp = service.GetCompanyNews(pb.GetCompanyNewsRequest(
            symbol="AAPL", from_date="2024-01-01", to_date="2024-12-31",
        ))
        a = resp.articles[0]
        assert a.url == "https://reuters.com/apple-iphone"
        assert a.datetime == 1700000000
        assert a.related == "AAPL"
        assert a.id == 123456

    def test_second_article(self, service):
        resp = service.GetCompanyNews(pb.GetCompanyNewsRequest(
            symbol="AAPL", from_date="2024-01-01", to_date="2024-12-31",
        ))
        assert resp.articles[1].headline == "Apple Reports Record Revenue"
        assert resp.articles[1].source == "CNBC"


class TestGetEarningsCalendar:
    def test_returns_earnings(self, service):
        resp = service.GetEarningsCalendar(pb.GetEarningsCalendarRequest(
            from_date="2024-01-01", to_date="2024-03-31",
        ))
        assert len(resp.earnings) == 2
        assert resp.earnings[0].symbol == "AAPL"
        assert resp.earnings[0].date == "2024-01-25"

    def test_earnings_estimates(self, service):
        resp = service.GetEarningsCalendar(pb.GetEarningsCalendarRequest(
            from_date="2024-01-01", to_date="2024-03-31",
        ))
        aapl = resp.earnings[0]
        assert aapl.eps_estimate == 2.10
        assert aapl.eps_actual == 2.18
        assert aapl.revenue_estimate == 118000000000
        assert aapl.revenue_actual == 119600000000

    def test_earnings_metadata(self, service):
        resp = service.GetEarningsCalendar(pb.GetEarningsCalendarRequest(
            from_date="2024-01-01", to_date="2024-03-31",
        ))
        aapl = resp.earnings[0]
        assert aapl.hour == "amc"
        assert aapl.quarter == 1
        assert aapl.year == 2024


class TestGetRecommendationTrends:
    def test_returns_trends(self, service):
        resp = service.GetRecommendationTrends(pb.GetRecommendationTrendsRequest(symbol="AAPL"))
        assert len(resp.trends) == 2
        assert resp.trends[0].period == "2024-01-01"

    def test_recommendation_counts(self, service):
        resp = service.GetRecommendationTrends(pb.GetRecommendationTrendsRequest(symbol="AAPL"))
        t = resp.trends[0]
        assert t.strong_buy == 15
        assert t.buy == 20
        assert t.hold == 8
        assert t.sell == 2
        assert t.strong_sell == 0

    def test_second_period(self, service):
        resp = service.GetRecommendationTrends(pb.GetRecommendationTrendsRequest(symbol="AAPL"))
        t = resp.trends[1]
        assert t.period == "2023-12-01"
        assert t.strong_buy == 14
        assert t.strong_sell == 1


class TestGetInsiderTransactions:
    def test_returns_transactions(self, service):
        resp = service.GetInsiderTransactions(pb.GetInsiderTransactionsRequest(symbol="AAPL"))
        assert len(resp.transactions) == 2
        assert resp.transactions[0].name == "Tim Cook"

    def test_transaction_fields(self, service):
        resp = service.GetInsiderTransactions(pb.GetInsiderTransactionsRequest(symbol="AAPL"))
        t = resp.transactions[0]
        assert t.share == 500000
        assert t.change == -50000
        assert t.filing_date == "2024-01-15"
        assert t.transaction_date == "2024-01-12"
        assert t.transaction_code == "S"
        assert t.transaction_price == 185.50

    def test_second_insider(self, service):
        resp = service.GetInsiderTransactions(pb.GetInsiderTransactionsRequest(symbol="AAPL"))
        t = resp.transactions[1]
        assert t.name == "Luca Maestri"
        assert t.transaction_price == 182.00


class TestGetMarketNews:
    def test_returns_news(self, service):
        resp = service.GetMarketNews(pb.GetMarketNewsRequest(category="general"))
        assert len(resp.articles) == 1
        assert resp.articles[0].headline == "Markets Rally on Fed Decision"
        assert resp.articles[0].source == "Bloomberg"

    def test_news_fields(self, service):
        resp = service.GetMarketNews(pb.GetMarketNewsRequest())
        a = resp.articles[0]
        assert a.url == "https://bloomberg.com/fed-decision"
        assert a.datetime == 1700000000
        assert a.category == "general"
        assert a.id == 789012


class TestGetPeers:
    def test_returns_peers(self, service):
        resp = service.GetPeers(pb.GetPeersRequest(symbol="AAPL"))
        assert len(resp.peers) == 5
        assert "MSFT" in resp.peers
        assert "GOOGL" in resp.peers
        assert "NVDA" in resp.peers


class TestGetBasicFinancials:
    def test_valuation_metrics(self, service):
        resp = service.GetBasicFinancials(pb.GetBasicFinancialsRequest(symbol="AAPL", metric="all"))
        assert resp.pe_trailing == 29.5
        assert resp.pb_quarterly == 47.2
        assert resp.eps_trailing == 6.05

    def test_price_range(self, service):
        resp = service.GetBasicFinancials(pb.GetBasicFinancialsRequest(symbol="AAPL", metric="all"))
        assert resp.week_52_high == 199.62
        assert resp.week_52_low == 143.90

    def test_margins(self, service):
        resp = service.GetBasicFinancials(pb.GetBasicFinancialsRequest(symbol="AAPL", metric="all"))
        assert resp.net_profit_margin_trailing == 25.31
        assert resp.gross_margin_trailing == 44.13
        assert resp.operating_margin_trailing == 29.82

    def test_other_metrics(self, service):
        resp = service.GetBasicFinancials(pb.GetBasicFinancialsRequest(symbol="AAPL", metric="all"))
        assert resp.beta == 1.29
        assert resp.dividend_yield_indicated == 0.55
        assert resp.roe_trailing == 160.09
        assert resp.total_debt_to_equity_quarterly == 176.30
        assert resp.ten_day_average_volume == 55.5
        assert resp.revenue_growth_quarterly_yoy == 2.07
        assert resp.market_capitalization == 2800000
