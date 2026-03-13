"""Shared fixtures for CoinGlass MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from coinglass_mcp.gen.coinglass.v1 import coinglass_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data -- matches real CoinGlass API return shapes
# ---------------------------------------------------------------------------

FAKE_FUNDING_RATE = {
    "code": "0",
    "msg": "success",
    "data": [
        {
            "symbol": "BTC",
            "exchangeList": [
                {
                    "exchange": "Binance",
                    "rate": 0.0001,
                    "predictedRate": 0.00012,
                },
                {
                    "exchange": "Bybit",
                    "rate": 0.00008,
                    "predictedRate": 0.0001,
                },
                {
                    "exchange": "OKX",
                    "rate": 0.00015,
                    "predictedRate": 0.00011,
                },
            ],
        },
        {
            "symbol": "ETH",
            "exchangeList": [
                {
                    "exchange": "Binance",
                    "rate": 0.00005,
                    "predictedRate": 0.00006,
                },
                {
                    "exchange": "Bybit",
                    "rate": 0.00004,
                    "predictedRate": 0.00005,
                },
            ],
        },
    ],
}

FAKE_FUNDING_RATE_BTC = {
    "code": "0",
    "msg": "success",
    "data": [
        {
            "symbol": "BTC",
            "exchangeList": [
                {
                    "exchange": "Binance",
                    "rate": 0.0001,
                    "predictedRate": 0.00012,
                },
                {
                    "exchange": "Bybit",
                    "rate": 0.00008,
                    "predictedRate": 0.0001,
                },
                {
                    "exchange": "OKX",
                    "rate": 0.00015,
                    "predictedRate": 0.00011,
                },
            ],
        },
    ],
}

FAKE_OPEN_INTEREST = {
    "code": "0",
    "msg": "success",
    "data": [
        {
            "exchange": "Binance",
            "openInterest": 5200000000.0,
            "openInterestAmount": 80000.5,
        },
        {
            "exchange": "Bybit",
            "openInterest": 2100000000.0,
            "openInterestAmount": 32000.25,
        },
        {
            "exchange": "OKX",
            "openInterest": 1800000000.0,
            "openInterestAmount": 27500.0,
        },
    ],
}

FAKE_LIQUIDATION = {
    "code": "0",
    "msg": "success",
    "data": [
        {
            "timestamp": 1700000000000,
            "longLiquidationUsd": 15000000.0,
            "shortLiquidationUsd": 8000000.0,
            "longCount": 1234,
            "shortCount": 567,
        },
        {
            "timestamp": 1700003600000,
            "longLiquidationUsd": 5000000.0,
            "shortLiquidationUsd": 12000000.0,
            "longCount": 456,
            "shortCount": 890,
        },
        {
            "timestamp": 1700007200000,
            "longLiquidationUsd": 3000000.0,
            "shortLiquidationUsd": 2000000.0,
            "longCount": 200,
            "shortCount": 150,
        },
    ],
}

FAKE_LONG_SHORT = {
    "code": "0",
    "msg": "success",
    "data": [
        {
            "timestamp": 1700000000000,
            "longRate": 0.52,
            "shortRate": 0.48,
            "longShortRatio": 1.083,
        },
        {
            "timestamp": 1700003600000,
            "longRate": 0.55,
            "shortRate": 0.45,
            "longShortRatio": 1.222,
        },
        {
            "timestamp": 1700007200000,
            "longRate": 0.49,
            "shortRate": 0.51,
            "longShortRatio": 0.961,
        },
    ],
}

FAKE_OI_HISTORY = {
    "code": "0",
    "msg": "success",
    "data": [
        {
            "timestamp": 1700000000000,
            "openInterest": 9500000000.0,
        },
        {
            "timestamp": 1700003600000,
            "openInterest": 9800000000.0,
        },
        {
            "timestamp": 1700007200000,
            "openInterest": 9200000000.0,
        },
        {
            "timestamp": 1700010800000,
            "openInterest": 9600000000.0,
        },
    ],
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/funding": FAKE_FUNDING_RATE,
        "/funding?symbol=BTC": FAKE_FUNDING_RATE_BTC,
        "/open_interest": FAKE_OPEN_INTEREST,
        "/liquidation_history": FAKE_LIQUIDATION,
        "/long_short": FAKE_LONG_SHORT,
        "/open_interest_history": FAKE_OI_HISTORY,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Match on path suffix; check parameterized paths first.
        # First pass: try paths with query params (more specific).
        for path, data in defaults.items():
            if "?" not in path:
                continue
            base_path, query = path.split("?", 1)
            if url.endswith(base_path):
                query_params = dict(p.split("=") for p in query.split("&"))
                if params and all(params.get(k) == v for k, v in query_params.items()):
                    resp.json.return_value = data
                    return resp
        # Second pass: try plain paths.
        for path, data in defaults.items():
            if "?" in path:
                continue
            if url.endswith(path):
                resp.json.return_value = data
                return resp
        resp.json.return_value = {"code": "0", "msg": "success", "data": []}
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """CoinGlassService with mocked HTTP client."""
    from coinglass_mcp.service import CoinGlassService

    svc = CoinGlassService.__new__(CoinGlassService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked CoinGlassService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-coinglass", version="0.0.1")
    srv.register(service)
    return srv
