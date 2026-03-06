"""Shared fixtures for Alpha Vantage MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from alphavantage_mcp.gen.alphavantage.v1 import alphavantage_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real Alpha Vantage API return shapes
# ---------------------------------------------------------------------------

FAKE_GLOBAL_QUOTE = {
    "Global Quote": {
        "01. symbol": "AAPL",
        "02. open": "182.3500",
        "03. high": "183.9200",
        "04. low": "181.4600",
        "05. price": "183.5800",
        "06. volume": "48425673",
        "07. latest trading day": "2025-01-15",
        "08. previous close": "181.1800",
        "09. change": "2.4000",
        "10. change percent": "1.3244%",
    }
}

FAKE_SYMBOL_SEARCH = {
    "bestMatches": [
        {
            "1. symbol": "AAPL",
            "2. name": "Apple Inc",
            "3. type": "Equity",
            "4. region": "United States",
            "5. marketOpen": "09:30",
            "6. marketClose": "16:00",
            "7. timezone": "UTC-04",
            "8. currency": "USD",
            "9. matchScore": "1.0000",
        },
        {
            "1. symbol": "APLE",
            "2. name": "Apple Hospitality REIT Inc",
            "3. type": "Equity",
            "4. region": "United States",
            "5. marketOpen": "09:30",
            "6. marketClose": "16:00",
            "7. timezone": "UTC-04",
            "8. currency": "USD",
            "9. matchScore": "0.8000",
        },
    ]
}

FAKE_DAILY_TIME_SERIES = {
    "Meta Data": {
        "1. Information": "Daily Prices (open, high, low, close) and Volumes",
        "2. Symbol": "AAPL",
        "3. Last Refreshed": "2025-01-15",
        "4. Output Size": "Compact",
        "5. Time Zone": "US/Eastern",
    },
    "Time Series (Daily)": {
        "2025-01-15": {
            "1. open": "182.3500",
            "2. high": "183.9200",
            "3. low": "181.4600",
            "4. close": "183.5800",
            "5. volume": "48425673",
        },
        "2025-01-14": {
            "1. open": "180.0000",
            "2. high": "182.0000",
            "3. low": "179.5000",
            "4. close": "181.1800",
            "5. volume": "55123456",
        },
    },
}

FAKE_WEEKLY_TIME_SERIES = {
    "Meta Data": {
        "1. Information": "Weekly Prices (open, high, low, close) and Volumes",
        "2. Symbol": "AAPL",
        "3. Last Refreshed": "2025-01-15",
        "4. Time Zone": "US/Eastern",
    },
    "Weekly Time Series": {
        "2025-01-15": {
            "1. open": "180.0000",
            "2. high": "185.0000",
            "3. low": "178.5000",
            "4. close": "183.5800",
            "5. volume": "200000000",
        },
        "2025-01-10": {
            "1. open": "176.0000",
            "2. high": "181.0000",
            "3. low": "175.0000",
            "4. close": "180.0000",
            "5. volume": "180000000",
        },
    },
}

FAKE_MONTHLY_TIME_SERIES = {
    "Meta Data": {
        "1. Information": "Monthly Prices (open, high, low, close) and Volumes",
        "2. Symbol": "AAPL",
        "3. Last Refreshed": "2025-01-15",
        "4. Time Zone": "US/Eastern",
    },
    "Monthly Time Series": {
        "2025-01-15": {
            "1. open": "175.0000",
            "2. high": "185.0000",
            "3. low": "172.0000",
            "4. close": "183.5800",
            "5. volume": "800000000",
        },
        "2024-12-31": {
            "1. open": "170.0000",
            "2. high": "178.0000",
            "3. low": "168.0000",
            "4. close": "175.0000",
            "5. volume": "750000000",
        },
    },
}

FAKE_SMA = {
    "Meta Data": {
        "1: Symbol": "AAPL",
        "2: Indicator": "Simple Moving Average (SMA)",
        "3: Last Refreshed": "2025-01-15",
        "4: Interval": "daily",
        "5: Time Period": 20,
        "6: Series Type": "close",
        "7: Time Zone": "US/Eastern",
    },
    "Technical Analysis: SMA": {
        "2025-01-15": {"SMA": "180.2500"},
        "2025-01-14": {"SMA": "179.8000"},
        "2025-01-13": {"SMA": "179.3500"},
    },
}

FAKE_RSI = {
    "Meta Data": {
        "1: Symbol": "AAPL",
        "2: Indicator": "Relative Strength Index (RSI)",
        "3: Last Refreshed": "2025-01-15",
        "4: Interval": "daily",
        "5: Time Period": 14,
        "6: Series Type": "close",
        "7: Time Zone": "US/Eastern",
    },
    "Technical Analysis: RSI": {
        "2025-01-15": {"RSI": "62.3400"},
        "2025-01-14": {"RSI": "58.1200"},
        "2025-01-13": {"RSI": "55.7800"},
    },
}

FAKE_MACD = {
    "Meta Data": {
        "1: Symbol": "AAPL",
        "2: Indicator": "Moving Average Convergence/Divergence (MACD)",
        "3: Last Refreshed": "2025-01-15",
        "4: Interval": "daily",
        "5.1: Fast Period": 12,
        "5.2: Slow Period": 26,
        "5.3: Signal Period": 9,
        "6: Series Type": "close",
        "7: Time Zone": "US/Eastern",
    },
    "Technical Analysis: MACD": {
        "2025-01-15": {
            "MACD": "1.2345",
            "MACD_Signal": "0.9876",
            "MACD_Hist": "0.2469",
        },
        "2025-01-14": {
            "MACD": "1.1000",
            "MACD_Signal": "0.9500",
            "MACD_Hist": "0.1500",
        },
    },
}

FAKE_COMPANY_OVERVIEW = {
    "Symbol": "AAPL",
    "Name": "Apple Inc",
    "Description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.",
    "Exchange": "NASDAQ",
    "Currency": "USD",
    "Country": "USA",
    "Sector": "TECHNOLOGY",
    "Industry": "ELECTRONIC COMPUTERS",
    "MarketCapitalization": "2850000000000",
    "PERatio": "29.50",
    "PEGRatio": "2.15",
    "BookValue": "4.38",
    "EPS": "6.42",
    "RevenuePerShareTTM": "24.32",
    "ProfitMargin": "0.264",
    "DividendPerShare": "0.96",
    "DividendYield": "0.0052",
    "52WeekHigh": "199.62",
    "52WeekLow": "164.08",
    "50DayMovingAverage": "185.23",
    "200DayMovingAverage": "181.45",
    "SharesOutstanding": "15115000000",
    "PriceToBookRatio": "41.92",
    "Beta": "1.24",
    "AnalystTargetPrice": "195.00",
    "ForwardPE": "28.10",
}

FAKE_EARNINGS = {
    "symbol": "AAPL",
    "annualEarnings": [
        {"fiscalDateEnding": "2024-09-30", "reportedEPS": "6.42"},
        {"fiscalDateEnding": "2023-09-30", "reportedEPS": "6.13"},
    ],
    "quarterlyEarnings": [
        {
            "fiscalDateEnding": "2024-09-30",
            "reportedDate": "2024-10-31",
            "reportedEPS": "1.64",
            "estimatedEPS": "1.60",
            "surprise": "0.04",
            "surprisePercentage": "2.5000",
        },
        {
            "fiscalDateEnding": "2024-06-30",
            "reportedDate": "2024-08-01",
            "reportedEPS": "1.40",
            "estimatedEPS": "1.35",
            "surprise": "0.05",
            "surprisePercentage": "3.7037",
        },
    ],
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses.

    Uses longest-match-wins: when the request params contain a 'function' key,
    that value is used for dispatch. Falls back to URL path matching.
    """
    function_map = {
        "GLOBAL_QUOTE": FAKE_GLOBAL_QUOTE,
        "SYMBOL_SEARCH": FAKE_SYMBOL_SEARCH,
        "TIME_SERIES_DAILY": FAKE_DAILY_TIME_SERIES,
        "TIME_SERIES_WEEKLY": FAKE_WEEKLY_TIME_SERIES,
        "TIME_SERIES_MONTHLY": FAKE_MONTHLY_TIME_SERIES,
        "SMA": FAKE_SMA,
        "RSI": FAKE_RSI,
        "MACD": FAKE_MACD,
        "OVERVIEW": FAKE_COMPANY_OVERVIEW,
        "EARNINGS": FAKE_EARNINGS,
    }
    if url_responses:
        function_map.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Dispatch on the 'function' query parameter.
        if params and "function" in params:
            fn = params["function"]
            resp.json.return_value = function_map.get(fn, {})
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
    """AlphaVantageService with mocked HTTP client."""
    from alphavantage_mcp.service import AlphaVantageService

    svc = AlphaVantageService.__new__(AlphaVantageService)
    svc._http = mock_http
    svc._api_key = "demo"
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked AlphaVantageService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-av", version="0.0.1")
    srv.register(service)
    return srv
