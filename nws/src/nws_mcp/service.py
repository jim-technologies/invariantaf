"""US National Weather Service API service implementation for Invariant Protocol."""

from __future__ import annotations

from typing import Any

import httpx
from google.protobuf import json_format

from nws_mcp.gen.nws.v1 import nws_pb2 as pb

DEFAULT_BASE_URL = "https://api.weather.gov"


class NwsService:
    """Implements NwsService -- public NWS weather data endpoints (no auth required)."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 15.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "invariant-mcp/1.0",
                "Accept": "application/geo+json",
            },
        )

    # -------------------------
    # RPC handlers
    # -------------------------

    def GetPointMetadata(
        self, request: pb.GetPointMetadataRequest, context: Any = None
    ) -> pb.GetPointMetadataResponse:
        lat = self._fmt_coord(request.latitude)
        lon = self._fmt_coord(request.longitude)
        data = self._get(f"/points/{lat},{lon}")
        props = data.get("properties", {})
        location = props.get("relativeLocation", {}).get("properties", {})
        return self._parse_message(
            {
                "office": props.get("gridId", ""),
                "grid_x": props.get("gridX", 0),
                "grid_y": props.get("gridY", 0),
                "forecast_url": props.get("forecast", ""),
                "forecast_hourly_url": props.get("forecastHourly", ""),
                "city": location.get("city", ""),
                "state": location.get("state", ""),
            },
            pb.GetPointMetadataResponse,
        )

    def GetForecast(
        self, request: pb.GetForecastRequest, context: Any = None
    ) -> pb.GetForecastResponse:
        office, gx, gy = self._resolve_grid(request.latitude, request.longitude)
        data = self._get(f"/gridpoints/{office}/{gx},{gy}/forecast")
        periods = self._extract_periods(data)
        return self._parse_message({"periods": periods}, pb.GetForecastResponse)

    def GetHourlyForecast(
        self, request: pb.GetHourlyForecastRequest, context: Any = None
    ) -> pb.GetHourlyForecastResponse:
        office, gx, gy = self._resolve_grid(request.latitude, request.longitude)
        data = self._get(f"/gridpoints/{office}/{gx},{gy}/forecast/hourly")
        periods = self._extract_periods(data)
        return self._parse_message({"periods": periods}, pb.GetHourlyForecastResponse)

    def GetAlerts(
        self, request: pb.GetAlertsRequest, context: Any = None
    ) -> pb.GetAlertsResponse:
        if self._has_field(request, "area"):
            data = self._get("/alerts/active", {"area": request.area})
        elif self._has_field(request, "latitude") and self._has_field(request, "longitude"):
            lat = self._fmt_coord(request.latitude)
            lon = self._fmt_coord(request.longitude)
            data = self._get("/alerts/active", {"point": f"{lat},{lon}"})
        else:
            return self._parse_message({"alerts": []}, pb.GetAlertsResponse)

        features = data.get("features", [])
        alerts = []
        for f in features:
            props = f.get("properties", {})
            alerts.append({
                "id": props.get("id", ""),
                "event": props.get("event", ""),
                "headline": props.get("headline", ""),
                "severity": props.get("severity", ""),
                "urgency": props.get("urgency", ""),
                "certainty": props.get("certainty", ""),
                "effective": props.get("effective", ""),
                "expires": props.get("expires", ""),
                "description": props.get("description", ""),
                "sender_name": props.get("senderName", ""),
                "area_desc": props.get("areaDesc", ""),
            })
        return self._parse_message({"alerts": alerts}, pb.GetAlertsResponse)

    def GetStations(
        self, request: pb.GetStationsRequest, context: Any = None
    ) -> pb.GetStationsResponse:
        lat = self._fmt_coord(request.latitude)
        lon = self._fmt_coord(request.longitude)
        data = self._get(f"/points/{lat},{lon}/stations")
        features = data.get("features", [])
        stations = []
        for f in features:
            props = f.get("properties", {})
            station_id = props.get("stationIdentifier", "")
            name = props.get("name", "")
            geom = f.get("geometry", {})
            coords = geom.get("coordinates", [0, 0])
            stations.append({
                "station_id": station_id,
                "name": name,
                "latitude": coords[1] if len(coords) > 1 else 0,
                "longitude": coords[0] if len(coords) > 0 else 0,
            })
        return self._parse_message({"stations": stations}, pb.GetStationsResponse)

    def GetLatestObservation(
        self, request: pb.GetLatestObservationRequest, context: Any = None
    ) -> pb.GetLatestObservationResponse:
        station_id = request.station_id
        data = self._get(f"/stations/{station_id}/observations/latest")
        props = data.get("properties", {})

        def _obs_value(raw: Any) -> dict[str, Any]:
            if not isinstance(raw, dict):
                return {"value": 0.0, "unit_code": ""}
            return {
                "value": raw.get("value") if raw.get("value") is not None else 0.0,
                "unit_code": raw.get("unitCode", ""),
            }

        return self._parse_message(
            {
                "station_id": station_id,
                "timestamp": props.get("timestamp", ""),
                "text_description": props.get("textDescription", ""),
                "temperature": _obs_value(props.get("temperature")),
                "dewpoint": _obs_value(props.get("dewpoint")),
                "wind_speed": _obs_value(props.get("windSpeed")),
                "wind_direction": _obs_value(props.get("windDirection")),
                "barometric_pressure": _obs_value(props.get("barometricPressure")),
                "relative_humidity": _obs_value(props.get("relativeHumidity")),
                "visibility": _obs_value(props.get("visibility")),
            },
            pb.GetLatestObservationResponse,
        )

    # -------------------------
    # Internal helpers
    # -------------------------

    def _resolve_grid(self, latitude: float, longitude: float) -> tuple[str, int, int]:
        """Resolve lat/lon to NWS grid coordinates via the /points endpoint."""
        lat = self._fmt_coord(latitude)
        lon = self._fmt_coord(longitude)
        data = self._get(f"/points/{lat},{lon}")
        props = data.get("properties", {})
        return props["gridId"], props["gridX"], props["gridY"]

    def _extract_periods(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract and normalize forecast periods from an NWS forecast response."""
        raw_periods = data.get("properties", {}).get("periods", [])
        periods = []
        for p in raw_periods:
            wind_speed = p.get("windSpeed", "")
            if isinstance(wind_speed, dict):
                wind_speed = str(wind_speed.get("value", ""))
            periods.append({
                "name": p.get("name", ""),
                "temperature": p.get("temperature", 0),
                "temperature_unit": p.get("temperatureUnit", ""),
                "wind_speed": str(wind_speed),
                "wind_direction": p.get("windDirection", ""),
                "short_forecast": p.get("shortForecast", ""),
                "detailed_forecast": p.get("detailedForecast", ""),
                "is_daytime": p.get("isDaytime", False),
                "start_time": p.get("startTime", ""),
                "end_time": p.get("endTime", ""),
            })
        return periods

    def _fmt_coord(self, value: float) -> str:
        """Format a coordinate to 4 decimal places (NWS API requirement)."""
        return f"{value:.4f}"

    # -------------------------
    # HTTP helpers
    # -------------------------

    def _get(self, path: str, query: dict[str, Any] | None = None) -> Any:
        url = self._build_url(path, query)
        response = self._client.request("GET", url)

        try:
            payload = response.json() if response.content else {}
        except Exception as exc:
            raise RuntimeError(f"GET {url}: invalid JSON response: {exc}") from exc

        if response.status_code >= 400:
            raise RuntimeError(f"GET {url}: HTTP {response.status_code}: {payload}")

        return payload

    def _build_url(self, path: str, query: dict[str, Any] | None = None) -> str:
        full = f"{self._base_url}{path}"
        if not query:
            return full
        import urllib.parse

        qs = urllib.parse.urlencode(
            [(k, str(v)) for k, v in query.items() if v is not None]
        )
        return f"{full}?{qs}" if qs else full

    # -------------------------
    # Generic helpers
    # -------------------------

    def _parse_message(self, payload: dict[str, Any], message_cls: type):
        message = message_cls()
        json_format.ParseDict(payload, message, ignore_unknown_fields=True)
        return message

    def _has_field(self, message: Any, field_name: str) -> bool:
        try:
            return bool(message.HasField(field_name))
        except ValueError:
            return False
