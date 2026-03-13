"""Live integration tests for NWS API -- hits the real API.

Run with:
    NWS_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) endpoints.
No API keys or credentials needed.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_BASE_URL = "https://api.weather.gov"

pytestmark = pytest.mark.skipif(
    os.getenv("NWS_RUN_LIVE_TESTS") != "1",
    reason="Set NWS_RUN_LIVE_TESTS=1 to run live NWS API tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    """Call a CLI method; skip on network errors or transient failures."""
    import httpx

    args = [service, method]
    if params:
        args.extend(["-r", json.dumps(params)])
    try:
        return live_server._cli(args)
    except (httpx.ConnectTimeout, httpx.ConnectError, httpx.TimeoutException) as exc:
        pytest.skip(f"{method}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        msg = str(exc)
        if any(code in msg for code in ("429", "500", "502", "503", "Timeout", "timed out")):
            pytest.skip(f"{method}: {msg[:120]}")
        raise


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from nws_mcp.gen.nws.v1 import nws_pb2 as _nws_pb2  # noqa: F401
    from nws_mcp.service import NwsService

    base_url = (os.getenv("NWS_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-nws-live", version="0.0.1"
    )
    servicer = NwsService(base_url=base_url)
    srv.register(servicer, service_name="nws.v1.NwsService")
    yield srv
    srv.stop()


# --- GetPointMetadata ---


class TestLiveGetPointMetadata:
    def test_nyc(self, live_server):
        result = _cli_or_skip(
            live_server, "NwsService", "GetPointMetadata",
            {"latitude": 40.7128, "longitude": -74.006},
        )
        assert result["office"] != ""
        assert result["grid_x"] > 0
        assert result["grid_y"] > 0
        assert result["city"] != ""
        assert result["state"] != ""

    def test_dallas(self, live_server):
        result = _cli_or_skip(
            live_server, "NwsService", "GetPointMetadata",
            {"latitude": 32.7767, "longitude": -96.797},
        )
        assert result["office"] != ""
        assert result["state"] == "TX"


# --- GetForecast ---


class TestLiveGetForecast:
    def test_nyc_forecast(self, live_server):
        result = _cli_or_skip(
            live_server, "NwsService", "GetForecast",
            {"latitude": 40.7128, "longitude": -74.006},
        )
        assert "periods" in result
        periods = result["periods"]
        assert isinstance(periods, list)
        assert len(periods) > 0
        p = periods[0]
        assert "name" in p
        assert "temperature" in p
        assert p["temperature_unit"] in ("F", "C")
        assert "short_forecast" in p

    def test_chicago_forecast(self, live_server):
        result = _cli_or_skip(
            live_server, "NwsService", "GetForecast",
            {"latitude": 41.8781, "longitude": -87.6298},
        )
        assert "periods" in result
        assert len(result["periods"]) > 0


# --- GetHourlyForecast ---


class TestLiveGetHourlyForecast:
    def test_nyc_hourly(self, live_server):
        result = _cli_or_skip(
            live_server, "NwsService", "GetHourlyForecast",
            {"latitude": 40.7128, "longitude": -74.006},
        )
        assert "periods" in result
        periods = result["periods"]
        assert isinstance(periods, list)
        assert len(periods) > 0
        p = periods[0]
        assert "temperature" in p
        assert p["temperature_unit"] in ("F", "C")


# --- GetAlerts ---


class TestLiveGetAlerts:
    def test_alerts_by_point(self, live_server):
        result = _cli_or_skip(
            live_server, "NwsService", "GetAlerts",
            {"latitude": 40.7128, "longitude": -74.006},
        )
        # There may or may not be active alerts; proto3 omits empty repeated fields.
        alerts = result.get("alerts", [])
        assert isinstance(alerts, list)

    def test_alerts_by_area(self, live_server):
        result = _cli_or_skip(
            live_server, "NwsService", "GetAlerts",
            {"area": "TX"},
        )
        # There may or may not be active alerts; proto3 omits empty repeated fields.
        alerts = result.get("alerts", [])
        assert isinstance(alerts, list)


# --- GetStations ---


class TestLiveGetStations:
    def test_nyc_stations(self, live_server):
        result = _cli_or_skip(
            live_server, "NwsService", "GetStations",
            {"latitude": 40.7128, "longitude": -74.006},
        )
        assert "stations" in result
        stations = result["stations"]
        assert isinstance(stations, list)
        assert len(stations) > 0
        s = stations[0]
        assert "station_id" in s
        assert "name" in s
        assert s["latitude"] != 0
        assert s["longitude"] != 0

    def test_dallas_stations(self, live_server):
        result = _cli_or_skip(
            live_server, "NwsService", "GetStations",
            {"latitude": 32.7767, "longitude": -96.797},
        )
        assert "stations" in result
        assert len(result["stations"]) > 0


# --- GetLatestObservation ---


class TestLiveGetLatestObservation:
    def test_observation_from_nyc_station(self, live_server):
        # First find a station near NYC
        stations_result = _cli_or_skip(
            live_server, "NwsService", "GetStations",
            {"latitude": 40.7128, "longitude": -74.006},
        )
        stations = stations_result.get("stations", [])
        if not stations:
            pytest.skip("No stations found near NYC")
        station_id = stations[0]["station_id"]

        result = _cli_or_skip(
            live_server, "NwsService", "GetLatestObservation",
            {"station_id": station_id},
        )
        assert result["station_id"] == station_id
        assert "timestamp" in result
        assert "temperature" in result
        assert "unit_code" in result["temperature"]

    def test_observation_kord(self, live_server):
        # Chicago O'Hare -- well-known station
        result = _cli_or_skip(
            live_server, "NwsService", "GetLatestObservation",
            {"station_id": "KORD"},
        )
        assert result["station_id"] == "KORD"
        assert "timestamp" in result
        assert "temperature" in result
