"""Shared fixtures for Marinade MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from marinade_mcp.gen.marinade.v1 import marinade_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data -- matches real Marinade API return shapes
# ---------------------------------------------------------------------------

FAKE_STAKE_STATS = {
    "value": 0.05954983746147113,
    "end_time": "2026-03-12T16:09:44Z",
    "end_price": 1.3659716275487495,
    "start_time": "2026-02-10T16:04:49Z",
    "start_price": 1.3594920492768106,
}

FAKE_VALIDATORS = {
    "validators": [
        {
            "identity": "HEL1USMZKAL2odpNBj2oCjffnFGaYwmbGmyewGv1e2TU",
            "vote_account": "he1iusunGwqrNtafDtLdhsUQDFvo13z9sUa36PauBtk",
            "info_name": "Helius",
            "info_url": "https://helius.dev",
            "info_icon_url": "https://helius-docs.s3.us-east-2.amazonaws.com/orange360x360.png",
            "commission_advertised": 0,
            "activated_stake": "14590505512992309",
            "marinade_stake": "0",
            "version": "3.1.8",
            "superminority": True,
            "credits": 4680701,
            "score": None,
            "dc_city": "Frankfurt",
            "dc_country": "Germany",
            "avg_uptime_pct": 0.9999813603918382,
            "avg_apy": 0.06186681193216703,
            "epochs_count": 344,
            "epoch_stats": [
                {
                    "epoch": 939,
                    "apy": None,
                    "skip_rate": 0.0,
                },
                {
                    "epoch": 938,
                    "apy": 0.061447726626806976,
                    "skip_rate": 0.0,
                },
            ],
        },
        {
            "identity": "Fd7btgySsrjuo25CJCj7oE7VPMyezDhnx7pZkj2v69Nk",
            "vote_account": "CcaHc2L43ZWjwCHART3oZoJvHLAe9hzT2DJNUpBzoTN1",
            "info_name": "Figment",
            "info_url": None,
            "info_icon_url": "https://hosted-assets-container-pbmv.s3.ca-central-1.amazonaws.com/f.png",
            "commission_advertised": 7,
            "activated_stake": "13219939472443357",
            "marinade_stake": "0",
            "version": "3.1.10",
            "superminority": True,
            "credits": 4678498,
            "score": None,
            "dc_city": "Frankfurt",
            "dc_country": "Germany",
            "avg_uptime_pct": 0.9997033742633578,
            "avg_apy": 0.05739468640780995,
            "epochs_count": 720,
            "epoch_stats": [
                {
                    "epoch": 939,
                    "apy": None,
                    "skip_rate": 0.0008760402978537085,
                },
                {
                    "epoch": 938,
                    "apy": 0.057016272029495774,
                    "skip_rate": 0.0011187350835322185,
                },
            ],
        },
    ],
    "validators_aggregated": [],
}

FAKE_MSOL_PRICE = 1.3659716275487495


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/msol/apy/30d": FAKE_STAKE_STATS,
        "/validators": FAKE_VALIDATORS,
        "/msol/price_sol": FAKE_MSOL_PRICE,
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
    """MarinadeService with mocked HTTP client."""
    from marinade_mcp.service import MarinadeService

    svc = MarinadeService.__new__(MarinadeService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked MarinadeService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-marinade", version="0.0.1")
    srv.register(service)
    return srv
