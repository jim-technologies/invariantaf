"""Live integration tests for OpenWeatherMap API -- hits the real API.

Run with:
    OPENWEATHERMAP_API_KEY=your_key OWM_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

Requires a free API key from https://openweathermap.org/api
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
    os.getenv("OWM_RUN_LIVE_TESTS") != "1",
    reason="Set OWM_RUN_LIVE_TESTS=1 to run live OpenWeatherMap API tests",
)


@pytest.fixture(scope="module")
def live_server():
    if not os.getenv("OPENWEATHERMAP_API_KEY"):
        pytest.skip("OPENWEATHERMAP_API_KEY required for live tests")

    from invariant import Server

    from openweathermap_mcp.service import OpenWeatherMapService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-owm-live", version="0.0.1"
    )
    servicer = OpenWeatherMapService()
    srv.register(servicer)
    yield srv
    srv.stop()


class TestLiveCurrentWeather:
    def test_get_by_city(self, live_server):
        result = live_server._cli(
            ["OpenWeatherMapService", "GetCurrentWeather", "-r", json.dumps({"city": "London"})]
        )
        assert "weather" in result
        w = result["weather"]
        assert "temp" in w
        assert "humidity" in w
        assert w.get("city_name") == "London"

    def test_get_by_coords(self, live_server):
        result = live_server._cli(
            ["OpenWeatherMapService", "GetCurrentWeatherByCoords", "-r", json.dumps({
                "lat": 40.7128, "lon": -74.006,
            })]
        )
        assert "weather" in result
        assert "temp" in result["weather"]


class TestLiveForecast:
    def test_get_forecast(self, live_server):
        result = live_server._cli(
            ["OpenWeatherMapService", "GetForecast", "-r", json.dumps({"city": "Tokyo"})]
        )
        assert "items" in result
        assert len(result["items"]) > 0
        item = result["items"][0]
        assert "temp" in item
        assert "dt" in item


class TestLiveAirQuality:
    def test_get_air_quality(self, live_server):
        result = live_server._cli(
            ["OpenWeatherMapService", "GetAirQuality", "-r", json.dumps({
                "lat": 51.5074, "lon": -0.1278,
            })]
        )
        assert "data" in result
        d = result["data"]
        assert "aqi" in d


class TestLiveGeocode:
    def test_geocode(self, live_server):
        result = live_server._cli(
            ["OpenWeatherMapService", "GetGeocode", "-r", json.dumps({"city": "Paris"})]
        )
        assert "locations" in result
        assert len(result["locations"]) > 0
        loc = result["locations"][0]
        assert "lat" in loc
        assert "lon" in loc
