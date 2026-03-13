"""Live integration tests for FRED API -- hits the real API.

Run with:
    FRED_API_KEY=your_key FRED_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

Requires a free FRED API key from https://fred.stlouisfed.org/docs/api/api_key.html
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
    os.getenv("FRED_RUN_LIVE_TESTS") != "1",
    reason="Set FRED_RUN_LIVE_TESTS=1 to run live FRED API tests",
)


@pytest.fixture(scope="module")
def live_server():
    if not os.getenv("FRED_API_KEY"):
        pytest.skip("FRED_API_KEY required for live tests")

    from invariant import Server

    from fred_mcp.service import FREDService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-fred-live", version="0.0.1"
    )
    servicer = FREDService()
    srv.register(servicer)
    yield srv
    srv.stop()


class TestLiveGetSeries:
    def test_get_gdp_series(self, live_server):
        result = live_server._cli(
            ["FREDService", "GetSeries", "-r", json.dumps({"series_id": "GDP"})]
        )
        assert "series" in result
        s = result["series"]
        assert s["id"] == "GDP"
        assert "title" in s

    def test_get_cpi_series(self, live_server):
        result = live_server._cli(
            ["FREDService", "GetSeries", "-r", json.dumps({"series_id": "CPIAUCSL"})]
        )
        assert result["series"]["id"] == "CPIAUCSL"


class TestLiveGetObservations:
    def test_get_gdp_observations(self, live_server):
        result = live_server._cli(
            ["FREDService", "GetSeriesObservations", "-r", json.dumps({
                "series_id": "GDP",
                "observation_start": "2024-01-01",
                "observation_end": "2024-12-31",
            })]
        )
        assert "observations" in result
        obs = result["observations"]
        assert isinstance(obs, list)
        assert len(obs) > 0
        assert "date" in obs[0]
        assert "value" in obs[0]


class TestLiveSearchSeries:
    def test_search_inflation(self, live_server):
        result = live_server._cli(
            ["FREDService", "SearchSeries", "-r", json.dumps({
                "search_text": "consumer price index",
                "limit": 5,
            })]
        )
        assert "results" in result
        assert len(result["results"]) > 0


class TestLiveCategories:
    def test_get_root_category(self, live_server):
        result = live_server._cli(
            ["FREDService", "GetCategory", "-r", json.dumps({"category_id": 0})]
        )
        assert "category" in result

    def test_get_category_children(self, live_server):
        result = live_server._cli(
            ["FREDService", "GetCategoryChildren", "-r", json.dumps({"category_id": 0})]
        )
        assert "categories" in result
        assert len(result["categories"]) > 0


class TestLiveReleases:
    def test_get_release(self, live_server):
        # Release 10 = Consumer Price Index
        result = live_server._cli(
            ["FREDService", "GetRelease", "-r", json.dumps({"release_id": 10})]
        )
        assert "release" in result
        assert result["release"]["id"] == 10
