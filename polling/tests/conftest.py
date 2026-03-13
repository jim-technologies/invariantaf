"""Shared fixtures for Polling MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from polling_mcp.gen.polling.v1 import polling_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data -- matches real PredictIt / Metaculus API return shapes
# ---------------------------------------------------------------------------

FAKE_PREDICTIT_CONTRACT_1 = {
    "id": 28901,
    "dateEnd": "2024-11-05T00:00:00",
    "name": "Republican",
    "shortName": "Republican",
    "status": "Open",
    "lastTradePrice": 0.55,
    "bestBuyYesCost": 0.56,
    "bestBuyNoCost": 0.46,
    "bestSellYesCost": 0.54,
    "bestSellNoCost": 0.44,
    "lastClosePrice": 0.54,
}

FAKE_PREDICTIT_CONTRACT_2 = {
    "id": 28902,
    "dateEnd": "2024-11-05T00:00:00",
    "name": "Democratic",
    "shortName": "Democratic",
    "status": "Open",
    "lastTradePrice": 0.48,
    "bestBuyYesCost": 0.49,
    "bestBuyNoCost": 0.53,
    "bestSellYesCost": 0.47,
    "bestSellNoCost": 0.51,
    "lastClosePrice": 0.47,
}

FAKE_PREDICTIT_MARKET_1 = {
    "id": 7456,
    "name": "Which party will win the 2024 presidential election?",
    "shortName": "2024 Presidential Election",
    "url": "https://www.predictit.org/markets/detail/7456",
    "status": "Open",
    "timeStamp": "2024-06-15T12:30:00Z",
    "image": "https://www.predictit.org/images/7456.png",
    "contracts": [FAKE_PREDICTIT_CONTRACT_1, FAKE_PREDICTIT_CONTRACT_2],
}

FAKE_PREDICTIT_MARKET_2 = {
    "id": 7500,
    "name": "Will there be a government shutdown in 2024?",
    "shortName": "Govt Shutdown 2024",
    "url": "https://www.predictit.org/markets/detail/7500",
    "status": "Open",
    "timeStamp": "2024-06-15T12:30:00Z",
    "image": "https://www.predictit.org/images/7500.png",
    "contracts": [
        {
            "id": 29001,
            "dateEnd": "2024-12-31T00:00:00",
            "name": "Yes",
            "shortName": "Yes",
            "status": "Open",
            "lastTradePrice": 0.35,
            "bestBuyYesCost": 0.36,
            "bestBuyNoCost": 0.66,
            "bestSellYesCost": 0.34,
            "bestSellNoCost": 0.64,
            "lastClosePrice": 0.34,
        },
    ],
}

FAKE_PREDICTIT_ALL = {
    "markets": [FAKE_PREDICTIT_MARKET_1, FAKE_PREDICTIT_MARKET_2],
}

FAKE_PREDICTIT_TICKER = {
    "id": 7456,
    "name": "Which party will win the 2024 presidential election?",
    "shortName": "2024 Presidential Election",
    "url": "https://www.predictit.org/markets/detail/7456",
    "status": "Open",
    "timeStamp": "2024-06-15T12:30:00Z",
    "image": "https://www.predictit.org/images/7456.png",
    "contracts": [FAKE_PREDICTIT_CONTRACT_1, FAKE_PREDICTIT_CONTRACT_2],
}

FAKE_METACULUS_QUESTION_1 = {
    "id": 10001,
    "title": "Will AI pass the Turing test by 2030?",
    "url": "https://www.metaculus.com/questions/10001/",
    "created_time": "2023-01-15T10:00:00Z",
    "publish_time": "2023-01-16T10:00:00Z",
    "close_time": "2029-12-31T23:59:59Z",
    "resolve_time": "2030-06-30T23:59:59Z",
    "number_of_predictions": 1250,
    "status": "open",
    "type": "binary",
    "community_prediction": {
        "full": {
            "q2": 0.72,
        },
    },
    "title_short": "AI Turing Test 2030",
    "resolution": None,
}

FAKE_METACULUS_QUESTION_2 = {
    "id": 10002,
    "title": "Will the US enter a recession in 2025?",
    "url": "https://www.metaculus.com/questions/10002/",
    "created_time": "2024-01-10T08:00:00Z",
    "publish_time": "2024-01-11T08:00:00Z",
    "close_time": "2025-12-31T23:59:59Z",
    "resolve_time": "2026-06-30T23:59:59Z",
    "number_of_predictions": 890,
    "status": "open",
    "type": "binary",
    "community_prediction": {
        "full": {
            "q2": 0.38,
        },
    },
    "title_short": "US Recession 2025",
    "resolution": None,
}

FAKE_METACULUS_RESOLVED = {
    "id": 9999,
    "title": "Will inflation exceed 5% in 2023?",
    "url": "https://www.metaculus.com/questions/9999/",
    "created_time": "2022-06-01T10:00:00Z",
    "publish_time": "2022-06-02T10:00:00Z",
    "close_time": "2023-12-31T23:59:59Z",
    "resolve_time": "2024-01-31T23:59:59Z",
    "number_of_predictions": 2100,
    "status": "resolved",
    "type": "binary",
    "community_prediction": {
        "full": {
            "q2": 0.65,
        },
    },
    "title_short": "Inflation >5% 2023",
    "resolution": 1.0,
}

FAKE_METACULUS_LIST = {
    "count": 3,
    "next": None,
    "previous": None,
    "results": [FAKE_METACULUS_QUESTION_1, FAKE_METACULUS_QUESTION_2, FAKE_METACULUS_RESOLVED],
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/api/marketdata/all/": FAKE_PREDICTIT_ALL,
        "/api/marketdata/ticker/PARTY.PRES2024/": FAKE_PREDICTIT_TICKER,
        "/api2/questions/": FAKE_METACULUS_LIST,
        "/api2/questions/10001/": FAKE_METACULUS_QUESTION_1,
        "/api2/questions/10002/": FAKE_METACULUS_QUESTION_2,
        "/api2/questions/9999/": FAKE_METACULUS_RESOLVED,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Match on path suffix.
        for path, data in defaults.items():
            if url.endswith(path):
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
    """PollingService with mocked HTTP client."""
    from polling_mcp.service import PollingService

    svc = PollingService.__new__(PollingService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked PollingService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-polling", version="0.0.1")
    srv.register(service)
    return srv
