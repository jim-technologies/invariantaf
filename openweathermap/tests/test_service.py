"""Unit tests — every OpenWeatherMapService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from openweathermap_mcp.gen.openweathermap.v1 import openweathermap_pb2 as pb
from tests.conftest import (
    FAKE_AIR_QUALITY,
    FAKE_CURRENT_WEATHER,
    FAKE_FORECAST,
    FAKE_GEOCODE,
    FAKE_HISTORICAL,
    FAKE_ONE_CALL,
    FAKE_REVERSE_GEOCODE,
    FAKE_UV_INDEX,
)


class TestGetCurrentWeather:
    def test_returns_weather(self, service):
        resp = service.GetCurrentWeather(pb.GetCurrentWeatherRequest(city="London"))
        assert resp.weather.city_name == "London"
        assert resp.weather.country == "GB"

    def test_temperature(self, service):
        resp = service.GetCurrentWeather(pb.GetCurrentWeatherRequest(city="London"))
        assert resp.weather.temp == 18.5
        assert resp.weather.feels_like == 17.2
        assert resp.weather.temp_min == 16.0
        assert resp.weather.temp_max == 20.0

    def test_humidity_and_pressure(self, service):
        resp = service.GetCurrentWeather(pb.GetCurrentWeatherRequest(city="London"))
        assert resp.weather.humidity == 65
        assert resp.weather.pressure == 1013

    def test_wind(self, service):
        resp = service.GetCurrentWeather(pb.GetCurrentWeatherRequest(city="London"))
        assert resp.weather.wind_speed == 3.5
        assert resp.weather.wind_deg == 220

    def test_weather_condition(self, service):
        resp = service.GetCurrentWeather(pb.GetCurrentWeatherRequest(city="London"))
        assert len(resp.weather.weather) == 1
        assert resp.weather.weather[0].main == "Clear"
        assert resp.weather.weather[0].description == "clear sky"
        assert resp.weather.weather[0].icon == "01d"

    def test_coordinates(self, service):
        resp = service.GetCurrentWeather(pb.GetCurrentWeatherRequest(city="London"))
        assert resp.weather.lat == 51.5074
        assert resp.weather.lon == -0.1278

    def test_sun_times(self, service):
        resp = service.GetCurrentWeather(pb.GetCurrentWeatherRequest(city="London"))
        assert resp.weather.sunrise == 1700000000
        assert resp.weather.sunset == 1700040000

    def test_passes_city_param(self, service, mock_http):
        service.GetCurrentWeather(pb.GetCurrentWeatherRequest(city="Tokyo"))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("q") == "Tokyo"

    def test_uses_metric_units(self, service, mock_http):
        service.GetCurrentWeather(pb.GetCurrentWeatherRequest(city="London"))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("units") == "metric"


class TestGetCurrentWeatherByCoords:
    def test_returns_weather(self, service):
        resp = service.GetCurrentWeatherByCoords(
            pb.GetCurrentWeatherByCoordsRequest(lat=51.5074, lon=-0.1278)
        )
        assert resp.weather.city_name == "London"
        assert resp.weather.temp == 18.5

    def test_passes_coords(self, service, mock_http):
        service.GetCurrentWeatherByCoords(
            pb.GetCurrentWeatherByCoordsRequest(lat=51.5074, lon=-0.1278)
        )
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("lat") == 51.5074
        assert params.get("lon") == -0.1278


class TestGetForecast:
    def test_returns_items(self, service):
        resp = service.GetForecast(pb.GetForecastRequest(city="London"))
        assert len(resp.items) == 2

    def test_city_info(self, service):
        resp = service.GetForecast(pb.GetForecastRequest(city="London"))
        assert resp.city_name == "London"
        assert resp.country == "GB"

    def test_first_item(self, service):
        resp = service.GetForecast(pb.GetForecastRequest(city="London"))
        item = resp.items[0]
        assert item.temp == 18.5
        assert item.humidity == 65
        assert item.wind_speed == 3.5
        assert item.pop == 0.1
        assert item.dt_txt == "2025-01-15 12:00:00"

    def test_weather_conditions(self, service):
        resp = service.GetForecast(pb.GetForecastRequest(city="London"))
        assert resp.items[0].weather[0].main == "Clear"
        assert resp.items[1].weather[0].main == "Clouds"

    def test_second_item(self, service):
        resp = service.GetForecast(pb.GetForecastRequest(city="London"))
        item = resp.items[1]
        assert item.temp == 16.0
        assert item.humidity == 75
        assert item.pop == 0.3


class TestGetAirQuality:
    def test_returns_data(self, service):
        resp = service.GetAirQuality(pb.GetAirQualityRequest(lat=51.5074, lon=-0.1278))
        assert resp.data is not None
        assert resp.data.aqi == 2

    def test_pollutants(self, service):
        resp = service.GetAirQuality(pb.GetAirQualityRequest(lat=51.5074, lon=-0.1278))
        assert resp.data.co == 230.31
        assert resp.data.no2 == 15.0
        assert resp.data.o3 == 68.5
        assert resp.data.pm2_5 == 12.5
        assert resp.data.pm10 == 18.3

    def test_timestamp(self, service):
        resp = service.GetAirQuality(pb.GetAirQualityRequest(lat=51.5074, lon=-0.1278))
        assert resp.data.dt == 1700020000

    def test_empty_list(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={"list": []})
        )
        resp = service.GetAirQuality(pb.GetAirQualityRequest(lat=0, lon=0))
        assert resp.data.aqi == 0


class TestGetUVIndex:
    def test_returns_uv(self, service):
        resp = service.GetUVIndex(pb.GetUVIndexRequest(lat=51.5074, lon=-0.1278))
        assert resp.uv_index == 5.2

    def test_coordinates(self, service):
        resp = service.GetUVIndex(pb.GetUVIndexRequest(lat=51.5074, lon=-0.1278))
        assert resp.lat == 51.5074
        assert resp.lon == -0.1278

    def test_timestamp(self, service):
        resp = service.GetUVIndex(pb.GetUVIndexRequest(lat=51.5074, lon=-0.1278))
        assert resp.dt == 1700020000


class TestGetGeocode:
    def test_returns_locations(self, service):
        resp = service.GetGeocode(pb.GetGeocodeRequest(city="London"))
        assert len(resp.locations) == 2

    def test_first_location(self, service):
        resp = service.GetGeocode(pb.GetGeocodeRequest(city="London"))
        loc = resp.locations[0]
        assert loc.name == "London"
        assert loc.lat == 51.5074
        assert loc.lon == -0.1278
        assert loc.country == "GB"
        assert loc.state == "England"

    def test_second_location(self, service):
        resp = service.GetGeocode(pb.GetGeocodeRequest(city="London"))
        loc = resp.locations[1]
        assert loc.country == "CA"
        assert loc.state == "Ontario"

    def test_passes_limit(self, service, mock_http):
        service.GetGeocode(pb.GetGeocodeRequest(city="London", limit=3))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("limit") == 3


class TestGetReverseGeocode:
    def test_returns_locations(self, service):
        resp = service.GetReverseGeocode(
            pb.GetReverseGeocodeRequest(lat=51.5074, lon=-0.1278)
        )
        assert len(resp.locations) == 1
        assert resp.locations[0].name == "London"

    def test_passes_coords(self, service, mock_http):
        service.GetReverseGeocode(
            pb.GetReverseGeocodeRequest(lat=51.5074, lon=-0.1278)
        )
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("lat") == 51.5074
        assert params.get("lon") == -0.1278


class TestGetOneCall:
    def test_current_weather(self, service):
        resp = service.GetOneCall(pb.GetOneCallRequest(lat=51.5074, lon=-0.1278))
        assert resp.current.temp == 18.5
        assert resp.current.feels_like == 17.2

    def test_metadata(self, service):
        resp = service.GetOneCall(pb.GetOneCallRequest(lat=51.5074, lon=-0.1278))
        assert resp.lat == 51.5074
        assert resp.lon == -0.1278
        assert resp.timezone == "Europe/London"

    def test_minutely(self, service):
        resp = service.GetOneCall(pb.GetOneCallRequest(lat=51.5074, lon=-0.1278))
        assert len(resp.minutely) == 2
        assert resp.minutely[0].precipitation == 0
        assert resp.minutely[1].precipitation == 0.5

    def test_hourly(self, service):
        resp = service.GetOneCall(pb.GetOneCallRequest(lat=51.5074, lon=-0.1278))
        assert len(resp.hourly) == 1
        assert resp.hourly[0].temp == 18.5
        assert resp.hourly[0].uvi == 5.2

    def test_daily(self, service):
        resp = service.GetOneCall(pb.GetOneCallRequest(lat=51.5074, lon=-0.1278))
        assert len(resp.daily) == 1
        d = resp.daily[0]
        assert d.temp_day == 18.5
        assert d.temp_night == 12.0
        assert d.temp_min == 10.0
        assert d.temp_max == 20.0
        assert d.summary == "Clear skies throughout the day"

    def test_alerts(self, service):
        resp = service.GetOneCall(pb.GetOneCallRequest(lat=51.5074, lon=-0.1278))
        assert len(resp.alerts) == 1
        alert = resp.alerts[0]
        assert alert.sender_name == "Met Office"
        assert alert.event == "Wind Advisory"
        assert alert.start == 1700020000
        assert alert.end == 1700060000


class TestGetHistoricalWeather:
    def test_returns_data(self, service):
        resp = service.GetHistoricalWeather(
            pb.GetHistoricalWeatherRequest(lat=51.5074, lon=-0.1278, dt=1700020000)
        )
        assert resp.data.temp == 15.0
        assert resp.data.feels_like == 13.5
        assert resp.data.humidity == 70

    def test_metadata(self, service):
        resp = service.GetHistoricalWeather(
            pb.GetHistoricalWeatherRequest(lat=51.5074, lon=-0.1278, dt=1700020000)
        )
        assert resp.lat == 51.5074
        assert resp.lon == -0.1278
        assert resp.timezone == "Europe/London"

    def test_weather_conditions(self, service):
        resp = service.GetHistoricalWeather(
            pb.GetHistoricalWeatherRequest(lat=51.5074, lon=-0.1278, dt=1700020000)
        )
        assert resp.data.weather[0].main == "Clouds"
        assert resp.data.weather[0].description == "scattered clouds"


class TestGetWeatherMap:
    def test_returns_url(self, service):
        resp = service.GetWeatherMap(
            pb.GetWeatherMapRequest(layer="clouds_new", z=5, x=15, y=10)
        )
        assert "tile.openweathermap.org" in resp.url
        assert "clouds_new/5/15/10.png" in resp.url

    def test_includes_api_key(self, service):
        resp = service.GetWeatherMap(
            pb.GetWeatherMapRequest(layer="temp_new", z=3, x=4, y=2)
        )
        assert "appid=test-key" in resp.url

    def test_default_layer(self, service):
        resp = service.GetWeatherMap(pb.GetWeatherMapRequest(z=1, x=0, y=0))
        assert "clouds_new" in resp.url

    def test_different_layers(self, service):
        for layer in ["precipitation_new", "pressure_new", "wind_new", "temp_new"]:
            resp = service.GetWeatherMap(
                pb.GetWeatherMapRequest(layer=layer, z=1, x=0, y=0)
            )
            assert layer in resp.url
