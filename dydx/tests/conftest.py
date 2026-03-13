"""Shared fixtures for dYdX MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dydx_mcp.gen.dydx.v1 import dydx_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real dYdX v4 Indexer API return shapes
# ---------------------------------------------------------------------------

FAKE_PERPETUAL_MARKETS = {
    "markets": {
        "BTC-USD": {
            "ticker": "BTC-USD",
            "status": "ACTIVE",
            "oraclePrice": "97500.00",
            "priceChange24H": "0.0215",
            "volume24H": "1250000000.50",
            "openInterest": "4500.123",
            "nextFundingRate": "0.000125",
            "stepSize": "0.0001",
            "tickSize": "1",
            "initialMarginFraction": "0.05",
            "maintenanceMarginFraction": "0.03",
            "openInterestUSDC": "438761175.00",
        },
        "ETH-USD": {
            "ticker": "ETH-USD",
            "status": "ACTIVE",
            "oraclePrice": "3450.00",
            "priceChange24H": "-0.0032",
            "volume24H": "850000000.25",
            "openInterest": "125000.5",
            "nextFundingRate": "-0.000050",
            "stepSize": "0.001",
            "tickSize": "0.1",
            "initialMarginFraction": "0.05",
            "maintenanceMarginFraction": "0.03",
            "openInterestUSDC": "431251725.00",
        },
    }
}

FAKE_ORDERBOOK = {
    "bids": [
        {"price": "97500.00", "size": "1.5"},
        {"price": "97499.00", "size": "2.3"},
        {"price": "97498.00", "size": "0.8"},
    ],
    "asks": [
        {"price": "97501.00", "size": "1.2"},
        {"price": "97502.00", "size": "3.1"},
        {"price": "97503.00", "size": "0.5"},
    ],
}

FAKE_TRADES = {
    "trades": [
        {
            "id": "trade-001",
            "side": "BUY",
            "price": "97500.50",
            "size": "0.5",
            "createdAt": "2026-03-12T10:30:00.000Z",
        },
        {
            "id": "trade-002",
            "side": "SELL",
            "price": "97499.00",
            "size": "1.2",
            "createdAt": "2026-03-12T10:29:55.000Z",
        },
        {
            "id": "trade-003",
            "side": "BUY",
            "price": "97501.00",
            "size": "0.1",
            "createdAt": "2026-03-12T10:29:50.000Z",
        },
    ]
}

FAKE_CANDLES = {
    "candles": [
        {
            "startedAt": "2026-03-12T10:00:00.000Z",
            "open": "97400.00",
            "high": "97600.00",
            "low": "97350.00",
            "close": "97500.00",
            "baseTokenVolume": "125.5",
            "usdVolume": "12231250.00",
            "trades": 1542,
            "resolution": "1HOUR",
        },
        {
            "startedAt": "2026-03-12T09:00:00.000Z",
            "open": "97300.00",
            "high": "97450.00",
            "low": "97200.00",
            "close": "97400.00",
            "baseTokenVolume": "98.3",
            "usdVolume": "9572790.00",
            "trades": 1203,
            "resolution": "1HOUR",
        },
    ]
}

FAKE_FUNDING_RATES = {
    "historicalFunding": [
        {
            "ticker": "BTC-USD",
            "rate": "0.000125",
            "price": "97500.00",
            "effectiveAt": "2026-03-12T10:00:00.000Z",
        },
        {
            "ticker": "BTC-USD",
            "rate": "0.000098",
            "price": "97450.00",
            "effectiveAt": "2026-03-12T09:00:00.000Z",
        },
        {
            "ticker": "BTC-USD",
            "rate": "-0.000015",
            "price": "97380.00",
            "effectiveAt": "2026-03-12T08:00:00.000Z",
        },
    ]
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/perpetualMarkets": FAKE_PERPETUAL_MARKETS,
        "/orderbooks/perpetualMarket/": FAKE_ORDERBOOK,
        "/trades/perpetualMarket/": FAKE_TRADES,
        "/candles/perpetualMarkets/": FAKE_CANDLES,
        "/historicalFunding/": FAKE_FUNDING_RATES,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Match on path suffix — try longer (more specific) paths first
        # to avoid e.g. "/perpetualMarkets" matching a candles URL.
        for path, data in sorted(defaults.items(), key=lambda kv: -len(kv[0])):
            if path in url:
                resp.json.return_value = data
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
    """DydxService with mocked HTTP client."""
    from dydx_mcp.service import DydxService

    svc = DydxService.__new__(DydxService)
    svc._base_url = "https://indexer.dydx.trade/v4"
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked DydxService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-dydx", version="0.0.1")
    srv.register(service)
    return srv
