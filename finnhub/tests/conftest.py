"""Shared fixtures for Finnhub MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from finnhub_mcp.gen.finnhub.v1 import finnhub_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real Finnhub API return shapes
# ---------------------------------------------------------------------------

FAKE_QUOTE = {
    "c": 178.72,       # current price
    "d": 2.38,         # change
    "dp": 1.35,        # percent change
    "h": 179.63,       # high
    "l": 176.21,       # low
    "o": 176.50,       # open
    "pc": 176.34,      # previous close
    "t": 1700000000,   # timestamp
}

FAKE_SEARCH = {
    "count": 2,
    "result": [
        {"symbol": "AAPL", "description": "Apple Inc", "displaySymbol": "AAPL", "type": "Common Stock"},
        {"symbol": "AAPL.SW", "description": "Apple Inc", "displaySymbol": "AAPL.SW", "type": "Common Stock"},
    ],
}

FAKE_COMPANY_PROFILE = {
    "ticker": "AAPL",
    "name": "Apple Inc",
    "country": "US",
    "currency": "USD",
    "exchange": "NASDAQ NMS - GLOBAL MARKET",
    "finnhubIndustry": "Technology",
    "ipo": "1980-12-12",
    "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/AAPL.png",
    "marketCapitalization": 2800000,
    "shareOutstanding": 15550.0,
    "weburl": "https://www.apple.com/",
    "phone": "14089961010",
}

FAKE_COMPANY_NEWS = [
    {
        "headline": "Apple Unveils New iPhone",
        "summary": "Apple announced the new iPhone at a special event.",
        "source": "Reuters",
        "url": "https://reuters.com/apple-iphone",
        "datetime": 1700000000,
        "related": "AAPL",
        "category": "company",
        "image": "https://img.reuters.com/apple.jpg",
        "id": 123456,
    },
    {
        "headline": "Apple Reports Record Revenue",
        "summary": "Apple's quarterly revenue exceeded expectations.",
        "source": "CNBC",
        "url": "https://cnbc.com/apple-revenue",
        "datetime": 1700100000,
        "related": "AAPL",
        "category": "company",
        "image": "https://img.cnbc.com/apple.jpg",
        "id": 123457,
    },
]

FAKE_EARNINGS = {
    "earningsCalendar": [
        {
            "symbol": "AAPL",
            "date": "2024-01-25",
            "hour": "amc",
            "quarter": 1,
            "year": 2024,
            "epsEstimate": 2.10,
            "epsActual": 2.18,
            "revenueEstimate": 118000000000,
            "revenueActual": 119600000000,
        },
        {
            "symbol": "MSFT",
            "date": "2024-01-23",
            "hour": "amc",
            "quarter": 2,
            "year": 2024,
            "epsEstimate": 2.78,
            "epsActual": 2.93,
            "revenueEstimate": 61000000000,
            "revenueActual": 62000000000,
        },
    ],
}

FAKE_RECOMMENDATION = [
    {
        "period": "2024-01-01",
        "strongBuy": 15,
        "buy": 20,
        "hold": 8,
        "sell": 2,
        "strongSell": 0,
    },
    {
        "period": "2023-12-01",
        "strongBuy": 14,
        "buy": 19,
        "hold": 9,
        "sell": 3,
        "strongSell": 1,
    },
]

FAKE_INSIDER_TRANSACTIONS = {
    "data": [
        {
            "name": "Tim Cook",
            "share": 500000,
            "change": -50000,
            "filingDate": "2024-01-15",
            "transactionDate": "2024-01-12",
            "transactionCode": "S",
            "transactionPrice": 185.50,
        },
        {
            "name": "Luca Maestri",
            "share": 200000,
            "change": -10000,
            "filingDate": "2024-01-10",
            "transactionDate": "2024-01-08",
            "transactionCode": "S",
            "transactionPrice": 182.00,
        },
    ],
}

FAKE_MARKET_NEWS = [
    {
        "headline": "Markets Rally on Fed Decision",
        "summary": "Stocks surged after the Federal Reserve held rates steady.",
        "source": "Bloomberg",
        "url": "https://bloomberg.com/fed-decision",
        "datetime": 1700000000,
        "related": "",
        "category": "general",
        "image": "https://img.bloomberg.com/fed.jpg",
        "id": 789012,
    },
]

FAKE_PEERS = ["MSFT", "GOOGL", "META", "AMZN", "NVDA"]

FAKE_BASIC_FINANCIALS = {
    "metric": {
        "peTTM": 29.5,
        "pbQuarterly": 47.2,
        "epsTTM": 6.05,
        "dividendYieldIndicatedAnnual": 0.55,
        "52WeekHigh": 199.62,
        "52WeekLow": 143.90,
        "roeTTM": 160.09,
        "totalDebt/totalEquityQuarterly": 176.30,
        "netProfitMarginTTM": 25.31,
        "grossMarginTTM": 44.13,
        "operatingMarginTTM": 29.82,
        "beta": 1.29,
        "10DayAverageTradingVolume": 55.5,
        "revenueGrowthQuarterlyYoy": 2.07,
        "marketCapitalization": 2800000,
    },
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses.

    Uses longest-match-wins so that e.g. '/stock/insider-transactions'
    matches before '/stock/recommendation'.
    """
    defaults = {
        "/quote": FAKE_QUOTE,
        "/search": FAKE_SEARCH,
        "/stock/profile2": FAKE_COMPANY_PROFILE,
        "/company-news": FAKE_COMPANY_NEWS,
        "/calendar/earnings": FAKE_EARNINGS,
        "/stock/recommendation": FAKE_RECOMMENDATION,
        "/stock/insider-transactions": FAKE_INSIDER_TRANSACTIONS,
        "/news": FAKE_MARKET_NEWS,
        "/stock/peers": FAKE_PEERS,
        "/stock/metric": FAKE_BASIC_FINANCIALS,
    }
    if url_responses:
        defaults.update(url_responses)

    # Sort paths longest-first so more specific paths match before shorter ones.
    sorted_paths = sorted(defaults.keys(), key=len, reverse=True)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        for path in sorted_paths:
            if path in url:
                resp.json.return_value = defaults[path]
                return resp
        resp.json.return_value = {}
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """FinnhubService with mocked HTTP client."""
    from finnhub_mcp.service import FinnhubService

    svc = FinnhubService.__new__(FinnhubService)
    svc._http = mock_http
    svc._api_key = "test-key"
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked FinnhubService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-fh", version="0.0.1")
    srv.register(service)
    return srv
