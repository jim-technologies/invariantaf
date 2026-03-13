"""Shared fixtures for BLS MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bls_mcp.gen.bls.v1 import bls_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data -- matches real BLS API v2 return shapes
# ---------------------------------------------------------------------------

FAKE_CPI_RESPONSE = {
    "status": "REQUEST_SUCCEEDED",
    "responseTime": 50,
    "message": [],
    "Results": {
        "series": [
            {
                "seriesID": "CUUR0000SA0",
                "data": [
                    {
                        "year": "2024",
                        "period": "M12",
                        "periodName": "December",
                        "latest": "true",
                        "value": "315.605",
                        "footnotes": [{}],
                    },
                    {
                        "year": "2024",
                        "period": "M11",
                        "periodName": "November",
                        "value": "314.175",
                        "footnotes": [{}],
                    },
                    {
                        "year": "2024",
                        "period": "M10",
                        "periodName": "October",
                        "value": "313.545",
                        "footnotes": [{}],
                    },
                ],
            }
        ]
    },
}

FAKE_UNEMPLOYMENT_RESPONSE = {
    "status": "REQUEST_SUCCEEDED",
    "responseTime": 45,
    "message": [],
    "Results": {
        "series": [
            {
                "seriesID": "LNS14000000",
                "data": [
                    {
                        "year": "2024",
                        "period": "M12",
                        "periodName": "December",
                        "latest": "true",
                        "value": "4.1",
                        "footnotes": [{}],
                    },
                    {
                        "year": "2024",
                        "period": "M11",
                        "periodName": "November",
                        "value": "4.2",
                        "footnotes": [{}],
                    },
                ],
            }
        ]
    },
}

FAKE_NONFARM_RESPONSE = {
    "status": "REQUEST_SUCCEEDED",
    "responseTime": 40,
    "message": [],
    "Results": {
        "series": [
            {
                "seriesID": "CES0000000001",
                "data": [
                    {
                        "year": "2024",
                        "period": "M12",
                        "periodName": "December",
                        "latest": "true",
                        "value": "157233",
                        "footnotes": [{"code": "P", "text": "Preliminary"}],
                    },
                    {
                        "year": "2024",
                        "period": "M11",
                        "periodName": "November",
                        "value": "156997",
                        "footnotes": [{}],
                    },
                ],
            }
        ]
    },
}

FAKE_MULTIPLE_SERIES_RESPONSE = {
    "status": "REQUEST_SUCCEEDED",
    "responseTime": 80,
    "message": [],
    "Results": {
        "series": [
            {
                "seriesID": "CUUR0000SA0",
                "data": [
                    {
                        "year": "2024",
                        "period": "M12",
                        "periodName": "December",
                        "latest": "true",
                        "value": "315.605",
                        "footnotes": [{}],
                    },
                ],
            },
            {
                "seriesID": "LNS14000000",
                "data": [
                    {
                        "year": "2024",
                        "period": "M12",
                        "periodName": "December",
                        "latest": "true",
                        "value": "4.1",
                        "footnotes": [{}],
                    },
                ],
            },
        ]
    },
}

FAKE_CATALOG_RESPONSE = {
    "status": "REQUEST_SUCCEEDED",
    "responseTime": 60,
    "message": [],
    "Results": {
        "series": [
            {
                "seriesID": "CUUR0000SA0",
                "catalog": {
                    "series_title": "All items in U.S. city average, all urban consumers, not seasonally adjusted",
                    "series_id": "CUUR0000SA0",
                    "seasonally_adjusted_code": "U",
                    "survey_name": "Consumer Price Index - All Urban Consumers",
                    "survey_abbreviation": "CU",
                },
                "data": [],
            },
            {
                "seriesID": "LNS14000000",
                "catalog": {
                    "series_title": "Unemployment Rate",
                    "series_id": "LNS14000000",
                    "seasonally_adjusted_code": "S",
                    "survey_name": "Labor Force Statistics from the Current Population Survey",
                    "survey_abbreviation": "LN",
                },
                "data": [],
            },
        ]
    },
}

FAKE_EMPTY_RESPONSE = {
    "status": "REQUEST_SUCCEEDED",
    "responseTime": 10,
    "message": [],
    "Results": {
        "series": []
    },
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses.

    The mock intercepts POST calls and returns different responses
    based on the series IDs in the request body.
    """
    http = MagicMock()

    def mock_post(url, json=None, headers=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()

        series_ids = (json or {}).get("seriesid", [])
        catalog = (json or {}).get("catalog", False)

        # Check for custom overrides first.
        if url_responses:
            key = ",".join(sorted(series_ids))
            if key in url_responses:
                resp.json.return_value = url_responses[key]
                return resp

        # Route based on series IDs and whether catalog is requested.
        if catalog:
            resp.json.return_value = FAKE_CATALOG_RESPONSE
        elif series_ids == ["CUUR0000SA0"]:
            resp.json.return_value = FAKE_CPI_RESPONSE
        elif series_ids == ["LNS14000000"]:
            resp.json.return_value = FAKE_UNEMPLOYMENT_RESPONSE
        elif series_ids == ["CES0000000001"]:
            resp.json.return_value = FAKE_NONFARM_RESPONSE
        elif len(series_ids) > 1:
            resp.json.return_value = FAKE_MULTIPLE_SERIES_RESPONSE
        else:
            resp.json.return_value = FAKE_EMPTY_RESPONSE

        return resp

    http.post = MagicMock(side_effect=mock_post)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """BLSService with mocked HTTP client."""
    from bls_mcp.service import BLSService

    svc = BLSService.__new__(BLSService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked BLSService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-bls", version="0.0.1")
    srv.register(service)
    return srv
