"""Live integration tests for USGS API -- hits real earthquake and water APIs.

Run with:
    USGS_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit the public USGS APIs. No API key or authentication required.
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
    os.getenv("USGS_RUN_LIVE_TESTS") != "1",
    reason="Set USGS_RUN_LIVE_TESTS=1 to run live USGS API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from usgs_mcp.service import USGSService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-usgs-live", version="0.0.1"
    )
    servicer = USGSService()
    srv.register(servicer)
    yield srv
    srv.stop()


def _cli_or_skip(live_server, args):
    """Call CLI and skip if the API returns an HTTP error."""
    try:
        return live_server._cli(args)
    except Exception as exc:
        msg = str(exc)
        if any(code in msg for code in ("404", "429", "500", "502", "503")) or "Timeout" in msg:
            pytest.skip(f"USGS API unavailable: {msg[:120]}")
        raise


class TestLiveRecentEarthquakes:
    def test_returns_collection(self, live_server):
        result = _cli_or_skip(live_server, ["USGSService", "GetRecentEarthquakes"])
        assert "collection" in result
        c = result["collection"]
        assert "count" in c
        assert "earthquakes" in c
        assert isinstance(c["earthquakes"], list)

    def test_earthquake_has_fields(self, live_server):
        result = _cli_or_skip(live_server, ["USGSService", "GetRecentEarthquakes"])
        eqs = result["collection"]["earthquakes"]
        if len(eqs) == 0:
            pytest.skip("No recent earthquakes in the last hour")
        eq = eqs[0]
        assert "id" in eq
        assert "magnitude" in eq
        assert "place" in eq


class TestLiveSignificantEarthquakes:
    def test_returns_collection(self, live_server):
        result = _cli_or_skip(live_server, ["USGSService", "GetSignificantEarthquakes"])
        assert "collection" in result
        c = result["collection"]
        assert "count" in c
        assert "earthquakes" in c


class TestLiveSearchEarthquakes:
    def test_search_by_magnitude(self, live_server):
        result = _cli_or_skip(
            live_server,
            [
                "USGSService",
                "SearchEarthquakes",
                "-r",
                json.dumps({
                    "start_time": "2024-01-01",
                    "end_time": "2024-01-31",
                    "min_magnitude": 5.0,
                    "limit": 5,
                }),
            ],
        )
        assert "collection" in result
        eqs = result["collection"]["earthquakes"]
        assert isinstance(eqs, list)
        # All returned should be >= 5.0
        for eq in eqs:
            assert eq["magnitude"] >= 5.0


class TestLiveEarthquakeDetail:
    def test_get_detail(self, live_server):
        # First search for a recent earthquake to get an ID
        result = _cli_or_skip(
            live_server,
            [
                "USGSService",
                "SearchEarthquakes",
                "-r",
                json.dumps({
                    "start_time": "2024-01-01",
                    "end_time": "2024-12-31",
                    "min_magnitude": 6.0,
                    "limit": 1,
                }),
            ],
        )
        eqs = result["collection"]["earthquakes"]
        if len(eqs) == 0:
            pytest.skip("No earthquakes found for detail lookup")
        event_id = eqs[0]["id"]

        detail = _cli_or_skip(
            live_server,
            [
                "USGSService",
                "GetEarthquakeDetail",
                "-r",
                json.dumps({"event_id": event_id}),
            ],
        )
        assert "earthquake" in detail
        assert detail["earthquake"]["id"] == event_id


class TestLiveWaterLevels:
    def test_potomac_river(self, live_server):
        """Potomac River at Little Falls -- a well-known, reliable gauge."""
        result = _cli_or_skip(
            live_server,
            [
                "USGSService",
                "GetWaterLevels",
                "-r",
                json.dumps({"site_number": "01646500"}),
            ],
        )
        assert "site" in result
        site = result["site"]
        assert site["site_number"] == "01646500"
        assert "POTOMAC" in site.get("site_name", "").upper()
        assert "readings" in site
        assert len(site["readings"]) > 0
