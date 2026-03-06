"""Shared fixtures for Alpaca MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from alpaca_mcp.gen.alpaca.v1 import alpaca_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real Alpaca API return shapes
# ---------------------------------------------------------------------------

FAKE_ACCOUNT = {
    "id": "904837e3-3b76-47ec-b432-046db621571b",
    "status": "ACTIVE",
    "currency": "USD",
    "buying_power": "50000.00",
    "cash": "25000.00",
    "portfolio_value": "75000.00",
    "equity": "75000.00",
    "last_equity": "74500.00",
    "long_market_value": "50000.00",
    "short_market_value": "0.00",
    "pattern_day_trader": False,
    "trading_blocked": False,
    "account_blocked": False,
}

FAKE_POSITIONS = [
    {
        "symbol": "AAPL",
        "qty": "10",
        "avg_entry_price": "175.50",
        "current_price": "182.30",
        "market_value": "1823.00",
        "unrealized_pl": "68.00",
        "unrealized_plpc": "0.0387",
        "asset_class": "us_equity",
        "side": "long",
        "exchange": "NASDAQ",
        "cost_basis": "1755.00",
    },
    {
        "symbol": "MSFT",
        "qty": "5",
        "avg_entry_price": "410.00",
        "current_price": "420.50",
        "market_value": "2102.50",
        "unrealized_pl": "52.50",
        "unrealized_plpc": "0.0256",
        "asset_class": "us_equity",
        "side": "long",
        "exchange": "NASDAQ",
        "cost_basis": "2050.00",
    },
]

FAKE_POSITION_AAPL = FAKE_POSITIONS[0]

FAKE_ORDER_PLACED = {
    "id": "61e69015-8549-4baf-b96e-8c4c0c2a4bfc",
    "status": "accepted",
    "symbol": "AAPL",
    "qty": "10",
    "side": "buy",
    "type": "limit",
    "time_in_force": "day",
    "limit_price": "180.00",
    "stop_price": None,
    "filled_avg_price": None,
    "filled_qty": "0",
    "created_at": "2025-01-15T10:00:00Z",
    "updated_at": "2025-01-15T10:00:00Z",
    "submitted_at": "2025-01-15T10:00:00Z",
    "filled_at": None,
    "asset_class": "us_equity",
}

FAKE_ORDERS = [
    {
        "id": "61e69015-8549-4baf-b96e-8c4c0c2a4bfc",
        "symbol": "AAPL",
        "qty": "10",
        "filled_qty": "0",
        "side": "buy",
        "type": "limit",
        "time_in_force": "day",
        "limit_price": "180.00",
        "stop_price": None,
        "filled_avg_price": None,
        "status": "new",
        "created_at": "2025-01-15T10:00:00Z",
        "updated_at": "2025-01-15T10:00:01Z",
        "submitted_at": "2025-01-15T10:00:00Z",
        "filled_at": None,
        "asset_class": "us_equity",
    },
    {
        "id": "b0b6dd9d-8b9b-48a7-8988-1c0f3c4e0f53",
        "symbol": "MSFT",
        "qty": "5",
        "filled_qty": "5",
        "side": "buy",
        "type": "market",
        "time_in_force": "day",
        "limit_price": None,
        "stop_price": None,
        "filled_avg_price": "420.50",
        "status": "filled",
        "created_at": "2025-01-14T14:30:00Z",
        "updated_at": "2025-01-14T14:30:01Z",
        "submitted_at": "2025-01-14T14:30:00Z",
        "filled_at": "2025-01-14T14:30:01Z",
        "asset_class": "us_equity",
    },
]

FAKE_ASSET = {
    "id": "b0b6dd9d-8b9b-48a7-8988-1c0f3c4e0f53",
    "class": "us_equity",
    "exchange": "NASDAQ",
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "tradable": True,
    "fractionable": True,
    "status": "active",
    "shortable": True,
    "marginable": True,
}

FAKE_BARS = {
    "bars": [
        {
            "t": "2025-01-13T05:00:00Z",
            "o": 178.50,
            "h": 182.00,
            "l": 177.80,
            "c": 181.20,
            "v": 65000000,
            "vw": 180.10,
            "n": 850000,
        },
        {
            "t": "2025-01-14T05:00:00Z",
            "o": 181.20,
            "h": 183.50,
            "l": 180.00,
            "c": 182.30,
            "v": 58000000,
            "vw": 181.80,
            "n": 720000,
        },
    ],
    "symbol": "AAPL",
    "next_page_token": None,
}

FAKE_LATEST_QUOTE = {
    "quote": {
        "bp": 182.25,
        "bs": 3,
        "ap": 182.30,
        "as": 5,
        "t": "2025-01-15T15:30:00.123Z",
    },
    "symbol": "AAPL",
}

FAKE_LATEST_TRADE = {
    "trade": {
        "p": 182.28,
        "s": 100,
        "x": "V",
        "t": "2025-01-15T15:30:00.456Z",
    },
    "symbol": "AAPL",
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable GET, POST, and DELETE responses."""
    get_defaults = {
        "/v2/account": FAKE_ACCOUNT,
        "/v2/positions": FAKE_POSITIONS,
        "/v2/positions/AAPL": FAKE_POSITION_AAPL,
        "/v2/orders": FAKE_ORDERS,
        "/v2/assets/AAPL": FAKE_ASSET,
        "/v2/stocks/AAPL/bars": FAKE_BARS,
        "/v2/stocks/AAPL/quotes/latest": FAKE_LATEST_QUOTE,
        "/v2/stocks/AAPL/trades/latest": FAKE_LATEST_TRADE,
    }
    post_defaults = {
        "/v2/orders": FAKE_ORDER_PLACED,
    }

    if url_responses:
        get_defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        for path, data in get_defaults.items():
            if url.endswith(path):
                resp.json.return_value = data
                return resp
        resp.json.return_value = {}
        return resp

    def mock_post(url, json=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        for path, data in post_defaults.items():
            if url.endswith(path):
                resp.json.return_value = data
                return resp
        resp.json.return_value = {}
        return resp

    def mock_delete(url):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        return resp

    http.get = MagicMock(side_effect=mock_get)
    http.post = MagicMock(side_effect=mock_post)
    http.delete = MagicMock(side_effect=mock_delete)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """AlpacaService with mocked HTTP client."""
    from alpaca_mcp.service import AlpacaService

    svc = AlpacaService.__new__(AlpacaService)
    svc._http = mock_http
    svc._base_url = "https://paper-api.alpaca.markets"
    svc._data_url = "https://data.alpaca.markets"
    svc._api_key = "test-key"
    svc._secret_key = "test-secret"
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked AlpacaService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-alpaca", version="0.0.1")
    srv.register(service)
    return srv
