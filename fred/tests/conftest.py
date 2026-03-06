"""Shared fixtures for FRED MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fred_mcp.gen.fred.v1 import fred_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real FRED API return shapes
# ---------------------------------------------------------------------------

FAKE_SERIES = {
    "seriess": [
        {
            "id": "GDP",
            "title": "Gross Domestic Product",
            "frequency": "Quarterly",
            "units": "Billions of Dollars",
            "seasonal_adjustment": "Seasonally Adjusted Annual Rate",
            "last_updated": "2024-12-19 07:51:03-06",
            "observation_start": "1947-01-01",
            "observation_end": "2024-07-01",
            "notes": "BEA Account Code: A191RC\nGross domestic product (GDP) is the value of goods and services produced.",
            "popularity": 93,
        }
    ]
}

FAKE_OBSERVATIONS = {
    "observations": [
        {"date": "2024-01-01", "value": "27956.998"},
        {"date": "2024-04-01", "value": "28277.367"},
        {"date": "2024-07-01", "value": "28571.460"},
    ]
}

FAKE_SEARCH = {
    "seriess": [
        {
            "id": "CPIAUCSL",
            "title": "Consumer Price Index for All Urban Consumers: All Items in U.S. City Average",
            "frequency": "Monthly",
            "units": "Index 1982-1984=100",
            "seasonal_adjustment": "Seasonally Adjusted",
            "last_updated": "2024-12-11 07:37:38-06",
            "observation_start": "1947-01-01",
            "observation_end": "2024-11-01",
            "notes": "Measures changes in the price level of consumer goods.",
            "popularity": 95,
        },
        {
            "id": "CPILFESL",
            "title": "Consumer Price Index for All Urban Consumers: All Items Less Food and Energy",
            "frequency": "Monthly",
            "units": "Index 1982-1984=100",
            "seasonal_adjustment": "Seasonally Adjusted",
            "last_updated": "2024-12-11 07:37:38-06",
            "observation_start": "1957-01-01",
            "observation_end": "2024-11-01",
            "notes": "Core CPI excluding volatile food and energy components.",
            "popularity": 88,
        },
    ],
    "count": 1532,
}

FAKE_CATEGORY = {
    "categories": [
        {"id": 32991, "name": "Prices", "parent_id": 0}
    ]
}

FAKE_CATEGORY_CHILDREN = {
    "categories": [
        {"id": 32992, "name": "Consumer Price Indexes (CPI and PCE)", "parent_id": 32991},
        {"id": 32993, "name": "Producer Price Indexes (PPI)", "parent_id": 32991},
    ]
}

FAKE_CATEGORY_SERIES = {
    "seriess": [
        {
            "id": "CPIAUCSL",
            "title": "Consumer Price Index for All Urban Consumers: All Items in U.S. City Average",
            "frequency": "Monthly",
            "units": "Index 1982-1984=100",
            "seasonal_adjustment": "Seasonally Adjusted",
            "last_updated": "2024-12-11 07:37:38-06",
            "observation_start": "1947-01-01",
            "observation_end": "2024-11-01",
            "notes": "",
            "popularity": 95,
        }
    ]
}

FAKE_RELEASE = {
    "releases": [
        {
            "id": 10,
            "name": "Consumer Price Index",
            "link": "https://www.bls.gov/cpi/",
            "notes": "The Consumer Price Index (CPI) is a measure of the average change over time in the prices paid by urban consumers.",
            "press_release": True,
        }
    ]
}

FAKE_RELEASE_DATES = {
    "release_dates": [
        {"release_id": 10, "release_name": "Consumer Price Index", "date": "2025-01-15"},
        {"release_id": 10, "release_name": "Consumer Price Index", "date": "2025-02-12"},
        {"release_id": 10, "release_name": "Consumer Price Index", "date": "2025-03-12"},
    ]
}

FAKE_RELEASE_SERIES = {
    "seriess": [
        {
            "id": "CPIAUCSL",
            "title": "Consumer Price Index for All Urban Consumers: All Items in U.S. City Average",
            "frequency": "Monthly",
            "units": "Index 1982-1984=100",
            "seasonal_adjustment": "Seasonally Adjusted",
            "last_updated": "2024-12-11 07:37:38-06",
            "observation_start": "1947-01-01",
            "observation_end": "2024-11-01",
            "notes": "",
            "popularity": 95,
        },
        {
            "id": "UNRATE",
            "title": "Unemployment Rate",
            "frequency": "Monthly",
            "units": "Percent",
            "seasonal_adjustment": "Seasonally Adjusted",
            "last_updated": "2024-12-06 07:44:04-06",
            "observation_start": "1948-01-01",
            "observation_end": "2024-11-01",
            "notes": "",
            "popularity": 96,
        },
    ]
}

FAKE_SERIES_CATEGORIES = {
    "categories": [
        {"id": 106, "name": "Gross Domestic Product", "parent_id": 18},
        {"id": 18, "name": "National Income & Product Accounts", "parent_id": 0},
    ]
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses.

    Uses longest-path-match-wins so that e.g. "series/observations" matches
    before "series" and "series/search" matches before "series".
    """
    defaults = {
        "/series/observations": FAKE_OBSERVATIONS,
        "/series/search": FAKE_SEARCH,
        "/series/categories": FAKE_SERIES_CATEGORIES,
        "/series": FAKE_SERIES,
        "/category/children": FAKE_CATEGORY_CHILDREN,
        "/category/series": FAKE_CATEGORY_SERIES,
        "/category": FAKE_CATEGORY,
        "/release/dates": FAKE_RELEASE_DATES,
        "/release/series": FAKE_RELEASE_SERIES,
        "/release": FAKE_RELEASE,
    }
    if url_responses:
        defaults.update(url_responses)

    # Sort by path length descending so longest match wins.
    sorted_paths = sorted(defaults.keys(), key=len, reverse=True)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        for path in sorted_paths:
            if url.endswith(path):
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
    """FREDService with mocked HTTP client."""
    from fred_mcp.service import FREDService

    svc = FREDService.__new__(FREDService)
    svc._http = mock_http
    svc._api_key = "test-key"
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked FREDService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-fred", version="0.0.1")
    srv.register(service)
    return srv
