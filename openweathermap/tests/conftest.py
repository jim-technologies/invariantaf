"""Shared fixtures for OpenWeatherMap MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openweathermap_mcp.gen.openweathermap.v1 import openweathermap_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real OpenWeatherMap API return shapes
# ---------------------------------------------------------------------------

FAKE_CURRENT_WEATHER = {
    "coord": {"lat": 51.5074, "lon": -0.1278},
    "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
    "main": {
        "temp": 18.5,
        "feels_like": 17.2,
        "temp_min": 16.0,
        "temp_max": 20.0,
        "humidity": 65,
        "pressure": 1013,
    },
    "wind": {"speed": 3.5, "deg": 220},
    "clouds": {"all": 10},
    "visibility": 10000,
    "sys": {"country": "GB", "sunrise": 1700000000, "sunset": 1700040000},
    "name": "London",
    "dt": 1700020000,
}

FAKE_FORECAST = {
    "list": [
        {
            "dt": 1700020000,
            "main": {
                "temp": 18.5, "feels_like": 17.2,
                "temp_min": 16.0, "temp_max": 20.0,
                "humidity": 65, "pressure": 1013,
            },
            "wind": {"speed": 3.5, "deg": 220},
            "clouds": {"all": 10},
            "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
            "pop": 0.1,
            "dt_txt": "2025-01-15 12:00:00",
        },
        {
            "dt": 1700030800,
            "main": {
                "temp": 16.0, "feels_like": 14.5,
                "temp_min": 14.0, "temp_max": 17.0,
                "humidity": 75, "pressure": 1012,
            },
            "wind": {"speed": 4.0, "deg": 200},
            "clouds": {"all": 40},
            "weather": [{"id": 802, "main": "Clouds", "description": "scattered clouds", "icon": "03d"}],
            "pop": 0.3,
            "dt_txt": "2025-01-15 15:00:00",
        },
    ],
    "city": {"name": "London", "country": "GB"},
}

FAKE_AIR_QUALITY = {
    "list": [
        {
            "main": {"aqi": 2},
            "components": {
                "co": 230.31,
                "no": 0.55,
                "no2": 15.0,
                "o3": 68.5,
                "so2": 3.2,
                "pm2_5": 12.5,
                "pm10": 18.3,
                "nh3": 1.5,
            },
            "dt": 1700020000,
        }
    ],
}

FAKE_UV_INDEX = {
    "value": 5.2,
    "date": 1700020000,
    "lat": 51.5074,
    "lon": -0.1278,
}

FAKE_GEOCODE = [
    {"name": "London", "lat": 51.5074, "lon": -0.1278, "country": "GB", "state": "England"},
    {"name": "London", "lat": 42.9834, "lon": -81.2330, "country": "CA", "state": "Ontario"},
]

FAKE_REVERSE_GEOCODE = [
    {"name": "London", "lat": 51.5074, "lon": -0.1278, "country": "GB", "state": "England"},
]

FAKE_ONE_CALL = {
    "lat": 51.5074,
    "lon": -0.1278,
    "timezone": "Europe/London",
    "current": {
        "dt": 1700020000,
        "temp": 18.5,
        "feels_like": 17.2,
        "humidity": 65,
        "pressure": 1013,
        "wind_speed": 3.5,
        "wind_deg": 220,
        "clouds": 10,
        "visibility": 10000,
        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
        "sunrise": 1700000000,
        "sunset": 1700040000,
    },
    "minutely": [
        {"dt": 1700020000, "precipitation": 0},
        {"dt": 1700020060, "precipitation": 0.5},
    ],
    "hourly": [
        {
            "dt": 1700020000, "temp": 18.5, "feels_like": 17.2,
            "humidity": 65, "pressure": 1013, "wind_speed": 3.5,
            "wind_deg": 220, "clouds": 10, "pop": 0.1,
            "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
            "uvi": 5.2,
        },
    ],
    "daily": [
        {
            "dt": 1700020000,
            "temp": {"day": 18.5, "night": 12.0, "min": 10.0, "max": 20.0},
            "feels_like": {"day": 17.2, "night": 10.5},
            "humidity": 65, "pressure": 1013, "wind_speed": 3.5,
            "wind_deg": 220, "clouds": 10, "pop": 0.1, "uvi": 5.2,
            "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
            "sunrise": 1700000000, "sunset": 1700040000,
            "summary": "Clear skies throughout the day",
        },
    ],
    "alerts": [
        {
            "sender_name": "Met Office",
            "event": "Wind Advisory",
            "start": 1700020000,
            "end": 1700060000,
            "description": "Strong winds expected in the evening.",
        },
    ],
}

FAKE_HISTORICAL = {
    "lat": 51.5074,
    "lon": -0.1278,
    "timezone": "Europe/London",
    "data": [
        {
            "dt": 1700020000,
            "temp": 15.0,
            "feels_like": 13.5,
            "humidity": 70,
            "pressure": 1010,
            "wind_speed": 4.0,
            "wind_deg": 180,
            "clouds": 50,
            "visibility": 8000,
            "weather": [{"id": 802, "main": "Clouds", "description": "scattered clouds", "icon": "03d"}],
            "sunrise": 1700000000,
            "sunset": 1700040000,
        },
    ],
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/data/2.5/weather": FAKE_CURRENT_WEATHER,
        "/data/2.5/forecast": FAKE_FORECAST,
        "/data/2.5/air_pollution": FAKE_AIR_QUALITY,
        "/data/2.5/uvi": FAKE_UV_INDEX,
        "/geo/1.0/direct": FAKE_GEOCODE,
        "/geo/1.0/reverse": FAKE_REVERSE_GEOCODE,
        "/data/3.0/onecall/timemachine": FAKE_HISTORICAL,
        "/data/3.0/onecall": FAKE_ONE_CALL,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Match on path suffix — try longer paths first to avoid
        # /data/3.0/onecall matching before /data/3.0/onecall/timemachine.
        for path in sorted(defaults.keys(), key=len, reverse=True):
            if url.endswith(path):
                resp.json.return_value = defaults[path]
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
    """OpenWeatherMapService with mocked HTTP client."""
    from openweathermap_mcp.service import OpenWeatherMapService

    svc = OpenWeatherMapService.__new__(OpenWeatherMapService)
    svc._http = mock_http
    svc._api_key = "test-key"
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked OpenWeatherMapService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-owm", version="0.0.1")
    srv.register(service)
    return srv
