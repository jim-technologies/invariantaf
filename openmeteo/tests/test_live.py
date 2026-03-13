"""Live integration tests for Open-Meteo API -- hits the real API.

Run with:
    OPENMETEO_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) endpoints.
No API keys or credentials needed.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

pytestmark = pytest.mark.skipif(
    os.getenv("OPENMETEO_RUN_LIVE_TESTS") != "1",
    reason="Set OPENMETEO_RUN_LIVE_TESTS=1 to run live Open-Meteo API tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    """Call a CLI method; skip on transient errors."""
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
    from openmeteo_mcp.gen.openmeteo.v1 import openmeteo_pb2 as _openmeteo_pb2  # noqa: F401
    from openmeteo_mcp.service import (
        DEFAULT_AIR_QUALITY_BASE_URL,
        DEFAULT_ARCHIVE_BASE_URL,
        DEFAULT_BASE_URL,
        DEFAULT_MARINE_BASE_URL,
        OpenMeteoService,
    )

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-openmeteo-live", version="0.0.1"
    )
    servicer = OpenMeteoService(
        base_url=DEFAULT_BASE_URL,
        archive_base_url=DEFAULT_ARCHIVE_BASE_URL,
        air_quality_base_url=DEFAULT_AIR_QUALITY_BASE_URL,
        marine_base_url=DEFAULT_MARINE_BASE_URL,
    )
    srv.register(servicer, service_name="openmeteo.v1.OpenMeteoService")
    yield srv
    srv.stop()


# --- GetForecast ---


class TestLiveGetForecast:
    def test_nyc_forecast(self, live_server):
        result = _cli_or_skip(
            live_server,
            "OpenMeteoService",
            "GetForecast",
            {"latitude": 40.7128, "longitude": -74.006},
        )
        assert "hourly" in result
        assert "daily" in result
        hourly = result["hourly"]
        assert len(hourly["times"]) > 0
        assert len(hourly["temperature_2m"]) > 0
        daily = result["daily"]
        assert len(daily["dates"]) > 0
        assert len(daily["temperature_2m_max"]) > 0
        assert len(daily["temperature_2m_min"]) > 0

    def test_tokyo_forecast(self, live_server):
        result = _cli_or_skip(
            live_server,
            "OpenMeteoService",
            "GetForecast",
            {"latitude": 35.6762, "longitude": 139.6503, "forecast_days": 3},
        )
        assert "hourly" in result
        assert "daily" in result
        daily = result["daily"]
        assert len(daily["dates"]) <= 3

    def test_london_forecast(self, live_server):
        result = _cli_or_skip(
            live_server,
            "OpenMeteoService",
            "GetForecast",
            {"latitude": 51.5074, "longitude": -0.1278, "timezone": "Europe/London"},
        )
        assert "hourly" in result
        assert "daily" in result


# --- GetHistoricalWeather ---


class TestLiveGetHistoricalWeather:
    def test_nyc_historical(self, live_server):
        result = _cli_or_skip(
            live_server,
            "OpenMeteoService",
            "GetHistoricalWeather",
            {
                "latitude": 40.7128,
                "longitude": -74.006,
                "start_date": "2024-01-01",
                "end_date": "2024-01-03",
            },
        )
        assert "hourly" in result
        assert "daily" in result
        daily = result["daily"]
        assert len(daily["dates"]) == 3
        assert len(daily["temperature_2m_max"]) == 3
        assert len(daily["temperature_2m_min"]) == 3

    def test_tokyo_historical(self, live_server):
        result = _cli_or_skip(
            live_server,
            "OpenMeteoService",
            "GetHistoricalWeather",
            {
                "latitude": 35.6762,
                "longitude": 139.6503,
                "start_date": "2024-07-01",
                "end_date": "2024-07-01",
            },
        )
        assert "daily" in result
        daily = result["daily"]
        assert len(daily["dates"]) == 1
        # Tokyo in July should be warm
        assert daily["temperature_2m_max"][0] > 20


# --- GetMultiModelForecast ---


class TestLiveGetMultiModelForecast:
    def test_nyc_multi_model(self, live_server):
        result = _cli_or_skip(
            live_server,
            "OpenMeteoService",
            "GetMultiModelForecast",
            {
                "latitude": 40.7128,
                "longitude": -74.006,
                "forecast_days": 3,
                "models": ["ecmwf_ifs025", "gfs_seamless", "icon_seamless"],
            },
        )
        assert "model_forecasts" in result
        forecasts = result["model_forecasts"]
        assert len(forecasts) >= 1  # At least one model should return data
        for f in forecasts:
            assert "model_name" in f
            assert "times" in f
            assert len(f["times"]) > 0
            assert len(f["temperature_2m"]) > 0

    def test_london_all_models(self, live_server):
        result = _cli_or_skip(
            live_server,
            "OpenMeteoService",
            "GetMultiModelForecast",
            {
                "latitude": 51.5074,
                "longitude": -0.1278,
                "forecast_days": 2,
                "models": [
                    "ecmwf_ifs025",
                    "gfs_seamless",
                    "icon_seamless",
                    "jma_seamless",
                    "gem_seamless",
                    "meteofrance_seamless",
                ],
            },
        )
        assert "model_forecasts" in result
        forecasts = result["model_forecasts"]
        assert len(forecasts) >= 3  # Most models should return data


# --- GetAirQuality ---


class TestLiveGetAirQuality:
    def test_nyc_air_quality(self, live_server):
        result = _cli_or_skip(
            live_server,
            "OpenMeteoService",
            "GetAirQuality",
            {"latitude": 40.7128, "longitude": -74.006},
        )
        assert "hourly" in result
        hourly = result["hourly"]
        assert len(hourly["times"]) > 0
        # At least some non-zero values should exist
        assert any(v > 0 for v in hourly.get("us_aqi", [0]))

    def test_tokyo_air_quality(self, live_server):
        result = _cli_or_skip(
            live_server,
            "OpenMeteoService",
            "GetAirQuality",
            {"latitude": 35.6762, "longitude": 139.6503},
        )
        assert "hourly" in result
        assert len(result["hourly"]["times"]) > 0


# --- GetMarineWeather ---


class TestLiveGetMarineWeather:
    def test_atlantic_marine(self, live_server):
        # Point in the Atlantic Ocean near NYC
        result = _cli_or_skip(
            live_server,
            "OpenMeteoService",
            "GetMarineWeather",
            {"latitude": 40.0, "longitude": -70.0},
        )
        assert "hourly" in result
        hourly = result["hourly"]
        assert len(hourly["times"]) > 0
        assert len(hourly["wave_height"]) > 0

    def test_pacific_marine(self, live_server):
        # Point in the Pacific Ocean near Tokyo
        result = _cli_or_skip(
            live_server,
            "OpenMeteoService",
            "GetMarineWeather",
            {"latitude": 34.0, "longitude": 140.0},
        )
        assert "hourly" in result
        assert len(result["hourly"]["times"]) > 0
