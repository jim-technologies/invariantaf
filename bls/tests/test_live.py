"""Live integration tests for BLS API -- hits the real API.

Run with:
    BLS_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit the public (unauthenticated) BLS API v2.
Set BLS_API_KEY for higher rate limits, but it is not required.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

pytestmark = pytest.mark.skipif(
    os.getenv("BLS_RUN_LIVE_TESTS") != "1",
    reason="Set BLS_RUN_LIVE_TESTS=1 to run live BLS API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from bls_mcp.service import BLSService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-bls-live", version="0.0.1"
    )
    servicer = BLSService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- GetSeriesData ---


class TestLiveGetSeriesData:
    def test_cpi_data(self, live_server):
        result = live_server._cli(
            ["BLSService", "GetSeriesData", "-r", json.dumps({
                "series_id": "CUUR0000SA0",
                "start_year": "2024",
                "end_year": "2024",
            })]
        )
        assert "series" in result
        series = result["series"]
        assert series.get("series_id") == "CUUR0000SA0"
        assert "observations" in series
        assert len(series["observations"]) > 0

    def test_observation_has_fields(self, live_server):
        result = live_server._cli(
            ["BLSService", "GetSeriesData", "-r", json.dumps({
                "series_id": "CUUR0000SA0",
                "start_year": "2024",
                "end_year": "2024",
            })]
        )
        obs = result["series"]["observations"][0]
        assert "year" in obs
        assert "period" in obs
        assert "value" in obs


# --- GetMultipleSeries ---


class TestLiveGetMultipleSeries:
    def test_multiple_series(self, live_server):
        result = live_server._cli(
            ["BLSService", "GetMultipleSeries", "-r", json.dumps({
                "series_ids": ["CUUR0000SA0", "LNS14000000"],
                "start_year": "2024",
                "end_year": "2024",
            })]
        )
        assert "series" in result
        series_list = result["series"]
        assert isinstance(series_list, list)
        assert len(series_list) == 2


# --- GetLatestCPI ---


class TestLiveGetLatestCPI:
    def test_returns_latest(self, live_server):
        result = live_server._cli(["BLSService", "GetLatestCPI"])
        assert result.get("series_id") == "CUUR0000SA0"
        assert "observation" in result
        obs = result["observation"]
        assert "value" in obs
        assert "year" in obs


# --- GetLatestUnemployment ---


class TestLiveGetLatestUnemployment:
    def test_returns_latest(self, live_server):
        result = live_server._cli(["BLSService", "GetLatestUnemployment"])
        assert result.get("series_id") == "LNS14000000"
        assert "observation" in result
        obs = result["observation"]
        assert "value" in obs


# --- GetLatestNonfarmPayrolls ---


class TestLiveGetLatestNonfarmPayrolls:
    def test_returns_latest(self, live_server):
        result = live_server._cli(["BLSService", "GetLatestNonfarmPayrolls"])
        assert result.get("series_id") == "CES0000000001"
        assert "observation" in result
        obs = result["observation"]
        assert "value" in obs


# --- SearchSeries ---


class TestLiveSearchSeries:
    def test_catalog_lookup(self, live_server):
        result = live_server._cli(
            ["BLSService", "SearchSeries", "-r", json.dumps({
                "series_ids": ["CUUR0000SA0"],
            })]
        )
        assert "results" in result
        results = result["results"]
        assert len(results) > 0
        r = results[0]
        assert "series_id" in r
