"""Live integration tests for SpaceX API -- hits the real API.

Run with:
    SPACEX_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) SpaceX v4 API endpoints.
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
    os.getenv("SPACEX_RUN_LIVE_TESTS") != "1",
    reason="Set SPACEX_RUN_LIVE_TESTS=1 to run live SpaceX API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from spacex_mcp.gen.spacex.v1 import spacex_pb2 as _spacex_pb2  # noqa: F401
    from spacex_mcp.service import SpaceXService
    from invariant import Server

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-spacex-live", version="0.0.1"
    )
    svc = SpaceXService()
    srv.register(svc)
    yield srv
    srv.stop()


# --- Shared fixtures ---


@pytest.fixture(scope="module")
def discovered_launch(live_server):
    """Discover a launch for tests that need a launch ID."""
    result = live_server._cli(["SpaceXService", "GetLatestLaunch"])
    launch = result.get("launch", {})
    assert launch, "expected a launch from GetLatestLaunch"
    return launch


@pytest.fixture(scope="module")
def discovered_rocket_id(live_server):
    """Discover a rocket ID for detail tests."""
    result = live_server._cli(["SpaceXService", "GetRockets"])
    rockets = result.get("rockets", [])
    assert rockets, "expected at least one rocket"
    return rockets[0]["id"]


# --- Company ---


class TestLiveCompany:
    def test_get_company_info(self, live_server):
        result = live_server._cli(["SpaceXService", "GetCompanyInfo"])
        assert result.get("name") == "SpaceX"
        assert result.get("founder") == "Elon Musk"
        assert result.get("ceo")
        assert isinstance(result.get("employees", 0), int)


# --- Launches ---


class TestLiveLaunches:
    def test_get_latest_launch(self, live_server):
        result = live_server._cli(["SpaceXService", "GetLatestLaunch"])
        assert "launch" in result
        launch = result["launch"]
        assert "name" in launch
        assert "id" in launch
        assert "flightNumber" in launch or "flight_number" in launch

    def test_get_launches(self, live_server):
        result = live_server._cli(["SpaceXService", "GetLaunches"])
        assert "launches" in result
        launches = result["launches"]
        assert isinstance(launches, list)
        assert len(launches) > 0

    def test_get_launch_by_id(self, live_server, discovered_launch):
        launch_id = discovered_launch.get("id", "")
        if not launch_id:
            pytest.skip("no launch id found")
        result = live_server._cli(
            ["SpaceXService", "GetLaunch", "-r", json.dumps({"id": launch_id})]
        )
        assert "launch" in result
        assert result["launch"]["id"] == launch_id

    def test_get_upcoming_launches(self, live_server):
        result = live_server._cli(["SpaceXService", "GetUpcomingLaunches"])
        assert "launches" in result
        launches = result["launches"]
        assert isinstance(launches, list)
        # Upcoming launches may be empty if none are scheduled
        if launches:
            assert "name" in launches[0]


# --- Rockets ---


class TestLiveRockets:
    def test_get_rockets(self, live_server):
        result = live_server._cli(["SpaceXService", "GetRockets"])
        assert "rockets" in result
        rockets = result["rockets"]
        assert isinstance(rockets, list)
        assert len(rockets) > 0
        r = rockets[0]
        assert "name" in r
        assert "id" in r

    def test_get_rocket_by_id(self, live_server, discovered_rocket_id):
        result = live_server._cli(
            ["SpaceXService", "GetRocket", "-r", json.dumps({"id": discovered_rocket_id})]
        )
        assert "rocket" in result
        rocket = result["rocket"]
        assert rocket["id"] == discovered_rocket_id
        assert "name" in rocket


# --- Crew ---


class TestLiveCrew:
    def test_get_crew(self, live_server):
        result = live_server._cli(["SpaceXService", "GetCrew"])
        assert "crew" in result
        crew = result["crew"]
        assert isinstance(crew, list)
        assert len(crew) > 0
        member = crew[0]
        assert "name" in member
        assert "agency" in member


# --- Starlink ---


class TestLiveStarlink:
    def test_get_starlink(self, live_server):
        result = live_server._cli(["SpaceXService", "GetStarlink"])
        assert "satellites" in result
        sats = result["satellites"]
        assert isinstance(sats, list)
        assert len(sats) > 0
        sat = sats[0]
        assert "id" in sat


# --- Launchpads ---


class TestLiveLaunchpads:
    def test_get_launchpads(self, live_server):
        result = live_server._cli(["SpaceXService", "GetLaunchpads"])
        assert "launchpads" in result
        pads = result["launchpads"]
        assert isinstance(pads, list)
        assert len(pads) > 0
        pad = pads[0]
        assert "name" in pad
        assert "status" in pad
