"""Shared fixtures for Lido MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lido_mcp.gen.lido.v1 import lido_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real Lido API return shapes
# ---------------------------------------------------------------------------

FAKE_APR_LAST = {
    "data": {
        "timeUnix": 1773318119,
        "apr": 2.464,
    },
    "meta": {
        "symbol": "stETH",
        "address": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",
        "chainId": 1,
    },
}

FAKE_APR_SMA = {
    "data": {
        "aprs": [
            {"timeUnix": 1772713319, "apr": 2.438},
            {"timeUnix": 1772799719, "apr": 2.34},
            {"timeUnix": 1772886071, "apr": 2.332},
            {"timeUnix": 1772972459, "apr": 2.338},
            {"timeUnix": 1773058919, "apr": 2.371},
            {"timeUnix": 1773145403, "apr": 2.384},
            {"timeUnix": 1773231791, "apr": 2.43},
            {"timeUnix": 1773318119, "apr": 2.464},
        ],
        "smaApr": 2.387125,
    },
    "meta": {
        "symbol": "stETH",
        "address": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",
        "chainId": 1,
    },
}

FAKE_WITHDRAWAL_TIME = {
    "requestInfo": {
        "finalizationIn": 427922000,
        "finalizationAt": "2026-03-17T12:30:23.056Z",
        "type": "exitValidators",
    },
    "status": "calculated",
    "nextCalculationAt": "2026-03-12T13:40:00.308Z",
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/v1/protocol/steth/apr/last": FAKE_APR_LAST,
        "/v1/protocol/steth/apr/sma": FAKE_APR_SMA,
        "/v2/request-time/calculate": FAKE_WITHDRAWAL_TIME,
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
    """LidoService with mocked HTTP client."""
    from lido_mcp.service import LidoService

    svc = LidoService.__new__(LidoService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked LidoService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-lido", version="0.0.1")
    srv.register(service)
    return srv
