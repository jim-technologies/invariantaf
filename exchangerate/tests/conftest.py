"""Shared fixtures for ExchangeRate MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from exchangerate_mcp.gen.exchangerate.v1 import exchangerate_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real Frankfurter API return shapes
# ---------------------------------------------------------------------------

FAKE_LATEST = {
    "base": "EUR",
    "date": "2025-01-15",
    "rates": {
        "USD": 1.0305,
        "GBP": 0.8451,
        "JPY": 161.52,
        "CHF": 0.9407,
        "CAD": 1.4912,
    },
}

FAKE_LATEST_FILTERED = {
    "base": "EUR",
    "date": "2025-01-15",
    "rates": {
        "USD": 1.0305,
        "GBP": 0.8451,
    },
}

FAKE_CONVERT = {
    "amount": 100.0,
    "base": "USD",
    "date": "2025-01-15",
    "rates": {
        "EUR": 97.04,
    },
}

FAKE_HISTORICAL = {
    "base": "EUR",
    "date": "2024-01-15",
    "rates": {
        "USD": 1.0891,
        "GBP": 0.8561,
        "JPY": 160.89,
    },
}

FAKE_HISTORICAL_FILTERED = {
    "base": "EUR",
    "date": "2024-01-15",
    "rates": {
        "USD": 1.0891,
        "GBP": 0.8561,
    },
}

FAKE_CONVERT_HISTORICAL = {
    "amount": 50.0,
    "base": "USD",
    "date": "2024-01-15",
    "rates": {
        "EUR": 45.91,
    },
}

FAKE_TIME_SERIES = {
    "base": "EUR",
    "start_date": "2025-01-10",
    "end_date": "2025-01-15",
    "rates": {
        "2025-01-10": {"USD": 1.0290, "GBP": 0.8430},
        "2025-01-13": {"USD": 1.0310, "GBP": 0.8445},
        "2025-01-14": {"USD": 1.0298, "GBP": 0.8440},
        "2025-01-15": {"USD": 1.0305, "GBP": 0.8451},
    },
}

FAKE_TIME_SERIES_PAIR = {
    "base": "USD",
    "start_date": "2025-01-10",
    "end_date": "2025-01-15",
    "rates": {
        "2025-01-10": {"EUR": 0.9718},
        "2025-01-13": {"EUR": 0.9699},
        "2025-01-14": {"EUR": 0.9711},
        "2025-01-15": {"EUR": 0.9704},
    },
}

FAKE_CURRENCIES = {
    "AUD": "Australian Dollar",
    "BGN": "Bulgarian Lev",
    "BRL": "Brazilian Real",
    "CAD": "Canadian Dollar",
    "CHF": "Swiss Franc",
    "CNY": "Chinese Renminbi Yuan",
    "EUR": "Euro",
    "GBP": "British Pound",
    "JPY": "Japanese Yen",
    "USD": "United States Dollar",
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        # Keyed by (path_fragment, has_amount, has_symbols) — but we simplify
        # by matching on URL path patterns.
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        params = params or {}

        # /currencies
        if "/currencies" in url:
            resp.json.return_value = FAKE_CURRENCIES
            return resp

        # Time series: contains ".."
        if ".." in url:
            if "symbols" in params and "," not in params.get("symbols", ""):
                resp.json.return_value = FAKE_TIME_SERIES_PAIR
            else:
                resp.json.return_value = FAKE_TIME_SERIES
            return resp

        # Historical date: path like /2024-01-15
        path = url.replace(_BASE_URL_FOR_MOCK, "")
        if path and path != "/latest" and not path.startswith("/latest"):
            # Historical
            if "amount" in params:
                resp.json.return_value = FAKE_CONVERT_HISTORICAL
            elif "symbols" in params:
                resp.json.return_value = FAKE_HISTORICAL_FILTERED
            else:
                resp.json.return_value = FAKE_HISTORICAL
            return resp

        # /latest with amount = Convert
        if "amount" in params:
            resp.json.return_value = FAKE_CONVERT
            return resp

        # /latest with symbols = filtered
        if "symbols" in params:
            resp.json.return_value = FAKE_LATEST_FILTERED
            return resp

        # /latest bare
        resp.json.return_value = FAKE_LATEST
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


# We need this for the mock to extract path from URL.
_BASE_URL_FOR_MOCK = "https://api.frankfurter.dev"


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """ExchangeRateService with mocked HTTP client."""
    from exchangerate_mcp.service import ExchangeRateService

    svc = ExchangeRateService.__new__(ExchangeRateService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked ExchangeRateService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-er", version="0.0.1")
    srv.register(service)
    return srv
