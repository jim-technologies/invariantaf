"""Open-Meteo weather data service implementation for Invariant Protocol."""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from openmeteo_mcp.gen.openmeteo.v1 import openmeteo_pb2 as pb

DEFAULT_BASE_URL = "https://api.open-meteo.com"
DEFAULT_ARCHIVE_BASE_URL = "https://archive-api.open-meteo.com"
DEFAULT_AIR_QUALITY_BASE_URL = "https://air-quality-api.open-meteo.com"
DEFAULT_MARINE_BASE_URL = "https://marine-api.open-meteo.com"

DEFAULT_MODELS = [
    "ecmwf_ifs025",
    "gfs_seamless",
    "icon_seamless",
    "jma_seamless",
    "gem_seamless",
    "meteofrance_seamless",
]


class OpenMeteoService:
    """Implements OpenMeteoService -- free weather data endpoints (no auth required)."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        archive_base_url: str = DEFAULT_ARCHIVE_BASE_URL,
        air_quality_base_url: str = DEFAULT_AIR_QUALITY_BASE_URL,
        marine_base_url: str = DEFAULT_MARINE_BASE_URL,
        timeout: float = 15.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._archive_base_url = archive_base_url.rstrip("/")
        self._air_quality_base_url = air_quality_base_url.rstrip("/")
        self._marine_base_url = marine_base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    # -------------------------
    # RPC handlers
    # -------------------------

    def GetForecast(
        self, request: pb.GetForecastRequest, context: Any = None
    ) -> pb.GetForecastResponse:
        forecast_days = request.forecast_days if self._has_field(request, "forecast_days") else 7
        timezone = request.timezone if self._has_field(request, "timezone") else "auto"

        query: dict[str, Any] = {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
            "timezone": timezone,
            "forecast_days": forecast_days,
        }

        payload = self._get(self._base_url, "/v1/forecast", query)
        return self._build_forecast_response(payload, pb.GetForecastResponse)

    def GetHistoricalWeather(
        self, request: pb.GetHistoricalWeatherRequest, context: Any = None
    ) -> pb.GetHistoricalWeatherResponse:
        timezone = request.timezone if self._has_field(request, "timezone") else "auto"

        query: dict[str, Any] = {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "hourly": "temperature_2m,precipitation",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": timezone,
        }

        payload = self._get(self._archive_base_url, "/v1/archive", query)
        return self._build_forecast_response(payload, pb.GetHistoricalWeatherResponse)

    def GetMultiModelForecast(
        self, request: pb.GetMultiModelForecastRequest, context: Any = None
    ) -> pb.GetMultiModelForecastResponse:
        forecast_days = request.forecast_days if self._has_field(request, "forecast_days") else 7
        models = list(request.models) if request.models else DEFAULT_MODELS

        query: dict[str, Any] = {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "hourly": "temperature_2m",
            "models": ",".join(models),
            "forecast_days": forecast_days,
        }

        payload = self._get(self._base_url, "/v1/forecast", query)
        return self._build_multi_model_response(payload, models)

    def GetAirQuality(
        self, request: pb.GetAirQualityRequest, context: Any = None
    ) -> pb.GetAirQualityResponse:
        query: dict[str, Any] = {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "hourly": "pm2_5,pm10,us_aqi",
        }

        payload = self._get(self._air_quality_base_url, "/v1/air-quality", query)
        return self._build_air_quality_response(payload)

    def GetMarineWeather(
        self, request: pb.GetMarineWeatherRequest, context: Any = None
    ) -> pb.GetMarineWeatherResponse:
        query: dict[str, Any] = {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "hourly": "wave_height,wave_period,wind_wave_height",
        }

        payload = self._get(self._marine_base_url, "/v1/marine", query)
        return self._build_marine_response(payload)

    # -------------------------
    # Response builders
    # -------------------------

    def _build_forecast_response(self, payload: dict[str, Any], message_cls: type):
        result: dict[str, Any] = {}

        hourly_raw = payload.get("hourly", {})
        if hourly_raw:
            result["hourly"] = {
                "times": hourly_raw.get("time", []),
                "temperature_2m": self._ensure_floats(hourly_raw.get("temperature_2m", [])),
                "relative_humidity_2m": self._ensure_floats(
                    hourly_raw.get("relative_humidity_2m", [])
                ),
                "precipitation": self._ensure_floats(hourly_raw.get("precipitation", [])),
                "wind_speed_10m": self._ensure_floats(hourly_raw.get("wind_speed_10m", [])),
                "weather_code": hourly_raw.get("weather_code", []),
            }

        daily_raw = payload.get("daily", {})
        if daily_raw:
            result["daily"] = {
                "dates": daily_raw.get("time", []),
                "temperature_2m_max": self._ensure_floats(
                    daily_raw.get("temperature_2m_max", [])
                ),
                "temperature_2m_min": self._ensure_floats(
                    daily_raw.get("temperature_2m_min", [])
                ),
                "precipitation_sum": self._ensure_floats(
                    daily_raw.get("precipitation_sum", [])
                ),
                "wind_speed_10m_max": self._ensure_floats(
                    daily_raw.get("wind_speed_10m_max", [])
                ),
            }

        return self._parse_message(result, message_cls)

    def _build_multi_model_response(
        self, payload: dict[str, Any], models: list[str]
    ) -> pb.GetMultiModelForecastResponse:
        hourly_raw = payload.get("hourly", {})
        times = hourly_raw.get("time", [])

        model_forecasts = []
        for model in models:
            # Open-Meteo returns per-model data as temperature_2m_<model_name>
            key = f"temperature_2m_{model}"
            temps = self._ensure_floats(hourly_raw.get(key, []))
            if temps:
                model_forecasts.append({
                    "model_name": model,
                    "times": times,
                    "temperature_2m": temps,
                })

        # Fallback: if no per-model keys found, use plain temperature_2m
        if not model_forecasts and "temperature_2m" in hourly_raw:
            temps = self._ensure_floats(hourly_raw.get("temperature_2m", []))
            for model in models:
                model_forecasts.append({
                    "model_name": model,
                    "times": times,
                    "temperature_2m": temps,
                })

        return self._parse_message(
            {"model_forecasts": model_forecasts}, pb.GetMultiModelForecastResponse
        )

    def _build_air_quality_response(
        self, payload: dict[str, Any]
    ) -> pb.GetAirQualityResponse:
        hourly_raw = payload.get("hourly", {})
        result: dict[str, Any] = {}

        if hourly_raw:
            result["hourly"] = {
                "times": hourly_raw.get("time", []),
                "pm2_5": self._ensure_floats(hourly_raw.get("pm2_5", [])),
                "pm10": self._ensure_floats(hourly_raw.get("pm10", [])),
                "us_aqi": self._ensure_floats(hourly_raw.get("us_aqi", [])),
            }

        return self._parse_message(result, pb.GetAirQualityResponse)

    def _build_marine_response(
        self, payload: dict[str, Any]
    ) -> pb.GetMarineWeatherResponse:
        hourly_raw = payload.get("hourly", {})
        result: dict[str, Any] = {}

        if hourly_raw:
            result["hourly"] = {
                "times": hourly_raw.get("time", []),
                "wave_height": self._ensure_floats(hourly_raw.get("wave_height", [])),
                "wave_period": self._ensure_floats(hourly_raw.get("wave_period", [])),
                "wind_wave_height": self._ensure_floats(
                    hourly_raw.get("wind_wave_height", [])
                ),
            }

        return self._parse_message(result, pb.GetMarineWeatherResponse)

    # -------------------------
    # HTTP helpers
    # -------------------------

    def _get(
        self, base_url: str, path: str, query: dict[str, Any] | None = None
    ) -> Any:
        url = self._build_url(base_url, path, query)
        response = self._client.request(
            "GET",
            url,
            headers={"Accept": "application/json"},
        )

        try:
            payload = response.json() if response.content else {}
        except Exception as exc:
            raise RuntimeError(f"GET {url}: invalid JSON response: {exc}") from exc

        if response.status_code >= 400:
            raise RuntimeError(f"GET {url}: HTTP {response.status_code}: {payload}")

        return payload

    def _build_url(
        self, base_url: str, path: str, query: dict[str, Any] | None = None
    ) -> str:
        full = f"{base_url}{path}"
        if not query:
            return full
        qs = urllib.parse.urlencode(
            [(k, self._to_http_scalar(v)) for k, v in query.items() if v is not None]
        )
        return f"{full}?{qs}" if qs else full

    def _to_http_scalar(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            return value
        if isinstance(value, int | float):
            return str(value)
        return str(value)

    # -------------------------
    # Generic helpers
    # -------------------------

    def _ensure_floats(self, values: list) -> list[float]:
        """Convert a list of values to floats, replacing None with 0.0."""
        return [float(v) if v is not None else 0.0 for v in values]

    def _parse_message(self, payload: dict[str, Any], message_cls: type):
        message = message_cls()
        json_format.ParseDict(payload, message, ignore_unknown_fields=True)
        return message

    def _has_field(self, message: Any, field_name: str) -> bool:
        try:
            return bool(message.HasField(field_name))
        except ValueError:
            return False
