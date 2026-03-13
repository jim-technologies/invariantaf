"""Shared fixtures for Dune Analytics MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dune_mcp.gen.dune.v1 import dune_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data -- matches real Dune API return shapes
# ---------------------------------------------------------------------------

FAKE_EXECUTE_RESPONSE = {
    "execution_id": "01HN7ABCDEF123456789",
    "state": "QUERY_STATE_PENDING",
}

FAKE_STATUS_PENDING = {
    "execution_id": "01HN7ABCDEF123456789",
    "query_id": 1234567,
    "state": "QUERY_STATE_EXECUTING",
    "submitted_at": "2024-01-15T10:30:00.000Z",
    "execution_started_at": "2024-01-15T10:30:01.000Z",
    "execution_ended_at": "",
    "expires_at": "",
}

FAKE_STATUS_COMPLETED = {
    "execution_id": "01HN7ABCDEF123456789",
    "query_id": 1234567,
    "state": "QUERY_STATE_COMPLETED",
    "submitted_at": "2024-01-15T10:30:00.000Z",
    "execution_started_at": "2024-01-15T10:30:01.000Z",
    "execution_ended_at": "2024-01-15T10:30:05.000Z",
    "expires_at": "2024-01-15T22:30:05.000Z",
}

FAKE_RESULTS = {
    "execution_id": "01HN7ABCDEF123456789",
    "query_id": 1234567,
    "state": "QUERY_STATE_COMPLETED",
    "submitted_at": "2024-01-15T10:30:00.000Z",
    "execution_started_at": "2024-01-15T10:30:01.000Z",
    "execution_ended_at": "2024-01-15T10:30:05.000Z",
    "expires_at": "2024-01-15T22:30:05.000Z",
    "result": {
        "metadata": {
            "column_names": ["block_date", "volume_usd", "tx_count"],
            "row_count": 3,
            "result_set_bytes": 1024,
            "total_row_count": 3,
            "truncated": False,
            "pending_time_millis": 150.5,
            "execution_time_millis": 3200.8,
        },
        "rows": [
            {
                "block_date": "2024-01-15",
                "volume_usd": 1500000000.50,
                "tx_count": 42000,
            },
            {
                "block_date": "2024-01-14",
                "volume_usd": 1350000000.75,
                "tx_count": 39500,
            },
            {
                "block_date": "2024-01-13",
                "volume_usd": 1200000000.25,
                "tx_count": 37000,
            },
        ],
    },
}

FAKE_LATEST_RESULTS = {
    "execution_id": "01HN7XYZABC987654321",
    "query_id": 7654321,
    "state": "QUERY_STATE_COMPLETED",
    "submitted_at": "2024-01-14T08:00:00.000Z",
    "execution_started_at": "2024-01-14T08:00:01.000Z",
    "execution_ended_at": "2024-01-14T08:00:03.000Z",
    "expires_at": "2024-01-14T20:00:03.000Z",
    "result": {
        "metadata": {
            "column_names": ["token", "holders", "market_cap"],
            "row_count": 2,
            "result_set_bytes": 512,
            "total_row_count": 2,
            "truncated": False,
            "pending_time_millis": 100.0,
            "execution_time_millis": 1500.0,
        },
        "rows": [
            {
                "token": "WETH",
                "holders": 500000,
                "market_cap": 250000000000,
            },
            {
                "token": "USDC",
                "holders": 1200000,
                "market_cap": 25000000000,
            },
        ],
    },
}

FAKE_CANCEL_RESPONSE = {
    "success": True,
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        ("POST", "/query/1234567/execute"): FAKE_EXECUTE_RESPONSE,
        ("GET", "/execution/01HN7ABCDEF123456789/status"): FAKE_STATUS_COMPLETED,
        ("GET", "/execution/01HN7PENDING/status"): FAKE_STATUS_PENDING,
        ("GET", "/execution/01HN7ABCDEF123456789/results"): FAKE_RESULTS,
        ("GET", "/query/7654321/results"): FAKE_LATEST_RESULTS,
        ("POST", "/execution/01HN7ABCDEF123456789/cancel"): FAKE_CANCEL_RESPONSE,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, headers=None, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        for (method, path), data in defaults.items():
            if method == "GET" and url.endswith(path):
                resp.json.return_value = data
                return resp
        resp.json.return_value = {}
        return resp

    def mock_post(url, headers=None, json=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        for (method, path), data in defaults.items():
            if method == "POST" and url.endswith(path):
                resp.json.return_value = data
                return resp
        resp.json.return_value = {}
        return resp

    http.get = MagicMock(side_effect=mock_get)
    http.post = MagicMock(side_effect=mock_post)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """DuneService with mocked HTTP client."""
    from dune_mcp.service import DuneService

    with patch.dict("os.environ", {"DUNE_API_KEY": "test_api_key_123"}):
        svc = DuneService.__new__(DuneService)
        svc._http = mock_http
        yield svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked DuneService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-dune", version="0.0.1")
    srv.register(service)
    return srv
