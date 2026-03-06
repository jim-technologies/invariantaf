"""OpenWeatherMapService — wraps the OpenWeatherMap API into proto RPCs."""

from __future__ import annotations

import os
from typing import Any

import httpx

from openweathermap_mcp.gen.openweathermap.v1 import openweathermap_pb2 as pb

_BASE_URL = "https://api.openweathermap.org"
_TILE_URL = "https://tile.openweathermap.org"


class OpenWeatherMapService:
    """Implements OpenWeatherMapService RPCs via the OpenWeatherMap API."""

    def __init__(self, *, api_key: str | None = None):
        self._http = httpx.Client(timeout=30)
        self._api_key = api_key or os.environ.get("OPENWEATHERMAP_API_KEY")

    def _get(self, path: str, params: dict | None = None) -> Any:
        p = dict(params or {})
        if self._api_key:
            p["appid"] = self._api_key
        resp = self._http.get(f"{_BASE_URL}{path}", params=p)
        resp.raise_for_status()
        return resp.json()

    def _parse_weather_conditions(self, weather_list: list) -> list:
        conditions = []
        for w in (weather_list or []):
            conditions.append(pb.WeatherCondition(
                id=w.get("id", 0),
                main=w.get("main", ""),
                description=w.get("description", ""),
                icon=w.get("icon", ""),
            ))
        return conditions

    def _parse_current_weather(self, raw: dict) -> pb.CurrentWeather:
        main = raw.get("main", {})
        wind = raw.get("wind", {})
        clouds = raw.get("clouds", {})
        sys_data = raw.get("sys", {})
        coord = raw.get("coord", {})
        return pb.CurrentWeather(
            temp=main.get("temp", 0),
            feels_like=main.get("feels_like", 0),
            temp_min=main.get("temp_min", 0),
            temp_max=main.get("temp_max", 0),
            humidity=main.get("humidity", 0),
            pressure=main.get("pressure", 0),
            wind_speed=wind.get("speed", 0),
            wind_deg=wind.get("deg", 0),
            clouds=clouds.get("all", 0),
            visibility=raw.get("visibility", 0),
            weather=self._parse_weather_conditions(raw.get("weather", [])),
            city_name=raw.get("name", ""),
            country=sys_data.get("country", ""),
            sunrise=sys_data.get("sunrise", 0),
            sunset=sys_data.get("sunset", 0),
            dt=raw.get("dt", 0),
            lat=coord.get("lat", 0),
            lon=coord.get("lon", 0),
        )

    def GetCurrentWeather(self, request: Any, context: Any = None) -> pb.GetCurrentWeatherResponse:
        raw = self._get("/data/2.5/weather", params={
            "q": request.city,
            "units": "metric",
        })
        return pb.GetCurrentWeatherResponse(
            weather=self._parse_current_weather(raw),
        )

    def GetCurrentWeatherByCoords(self, request: Any, context: Any = None) -> pb.GetCurrentWeatherResponse:
        raw = self._get("/data/2.5/weather", params={
            "lat": request.lat,
            "lon": request.lon,
            "units": "metric",
        })
        return pb.GetCurrentWeatherResponse(
            weather=self._parse_current_weather(raw),
        )

    def GetForecast(self, request: Any, context: Any = None) -> pb.GetForecastResponse:
        raw = self._get("/data/2.5/forecast", params={
            "q": request.city,
            "units": "metric",
        })
        resp = pb.GetForecastResponse()
        city = raw.get("city", {})
        resp.city_name = city.get("name", "")
        resp.country = city.get("country", "")
        for item in raw.get("list", []):
            main = item.get("main", {})
            wind = item.get("wind", {})
            clouds = item.get("clouds", {})
            resp.items.append(pb.ForecastItem(
                dt=item.get("dt", 0),
                temp=main.get("temp", 0),
                feels_like=main.get("feels_like", 0),
                temp_min=main.get("temp_min", 0),
                temp_max=main.get("temp_max", 0),
                humidity=main.get("humidity", 0),
                pressure=main.get("pressure", 0),
                wind_speed=wind.get("speed", 0),
                wind_deg=wind.get("deg", 0),
                clouds=clouds.get("all", 0),
                weather=self._parse_weather_conditions(item.get("weather", [])),
                pop=item.get("pop", 0),
                dt_txt=item.get("dt_txt", ""),
            ))
        return resp

    def GetAirQuality(self, request: Any, context: Any = None) -> pb.GetAirQualityResponse:
        raw = self._get("/data/2.5/air_pollution", params={
            "lat": request.lat,
            "lon": request.lon,
        })
        items = raw.get("list", [])
        if not items:
            return pb.GetAirQualityResponse()
        item = items[0]
        main = item.get("main", {})
        components = item.get("components", {})
        return pb.GetAirQualityResponse(
            data=pb.AirQualityData(
                aqi=main.get("aqi", 0),
                co=components.get("co", 0),
                no=components.get("no", 0),
                no2=components.get("no2", 0),
                o3=components.get("o3", 0),
                so2=components.get("so2", 0),
                pm2_5=components.get("pm2_5", 0),
                pm10=components.get("pm10", 0),
                nh3=components.get("nh3", 0),
                dt=item.get("dt", 0),
            ),
        )

    def GetUVIndex(self, request: Any, context: Any = None) -> pb.GetUVIndexResponse:
        raw = self._get("/data/2.5/uvi", params={
            "lat": request.lat,
            "lon": request.lon,
        })
        return pb.GetUVIndexResponse(
            uv_index=raw.get("value", 0),
            dt=raw.get("date", 0),
            lat=raw.get("lat", 0),
            lon=raw.get("lon", 0),
        )

    def GetGeocode(self, request: Any, context: Any = None) -> pb.GetGeocodeResponse:
        raw = self._get("/geo/1.0/direct", params={
            "q": request.city,
            "limit": request.limit or 5,
        })
        resp = pb.GetGeocodeResponse()
        for loc in raw:
            resp.locations.append(pb.GeoLocation(
                name=loc.get("name", ""),
                lat=loc.get("lat", 0),
                lon=loc.get("lon", 0),
                country=loc.get("country", ""),
                state=loc.get("state", ""),
            ))
        return resp

    def GetReverseGeocode(self, request: Any, context: Any = None) -> pb.GetReverseGeocodeResponse:
        raw = self._get("/geo/1.0/reverse", params={
            "lat": request.lat,
            "lon": request.lon,
            "limit": request.limit or 5,
        })
        resp = pb.GetReverseGeocodeResponse()
        for loc in raw:
            resp.locations.append(pb.GeoLocation(
                name=loc.get("name", ""),
                lat=loc.get("lat", 0),
                lon=loc.get("lon", 0),
                country=loc.get("country", ""),
                state=loc.get("state", ""),
            ))
        return resp

    def GetOneCall(self, request: Any, context: Any = None) -> pb.GetOneCallResponse:
        raw = self._get("/data/3.0/onecall", params={
            "lat": request.lat,
            "lon": request.lon,
            "units": "metric",
        })
        resp = pb.GetOneCallResponse()
        resp.lat = raw.get("lat", 0)
        resp.lon = raw.get("lon", 0)
        resp.timezone = raw.get("timezone", "")

        # Current weather
        current = raw.get("current", {})
        if current:
            resp.current.CopyFrom(pb.CurrentWeather(
                temp=current.get("temp", 0),
                feels_like=current.get("feels_like", 0),
                humidity=current.get("humidity", 0),
                pressure=current.get("pressure", 0),
                wind_speed=current.get("wind_speed", 0),
                wind_deg=current.get("wind_deg", 0),
                clouds=current.get("clouds", 0),
                visibility=current.get("visibility", 0),
                weather=self._parse_weather_conditions(current.get("weather", [])),
                sunrise=current.get("sunrise", 0),
                sunset=current.get("sunset", 0),
                dt=current.get("dt", 0),
                lat=raw.get("lat", 0),
                lon=raw.get("lon", 0),
            ))

        # Minutely precipitation
        for m in raw.get("minutely", []):
            resp.minutely.append(pb.MinutelyPrecipitation(
                dt=m.get("dt", 0),
                precipitation=m.get("precipitation", 0),
            ))

        # Hourly forecast
        for h in raw.get("hourly", []):
            resp.hourly.append(pb.HourlyForecast(
                dt=h.get("dt", 0),
                temp=h.get("temp", 0),
                feels_like=h.get("feels_like", 0),
                humidity=h.get("humidity", 0),
                pressure=h.get("pressure", 0),
                wind_speed=h.get("wind_speed", 0),
                wind_deg=h.get("wind_deg", 0),
                clouds=h.get("clouds", 0),
                pop=h.get("pop", 0),
                weather=self._parse_weather_conditions(h.get("weather", [])),
                uvi=h.get("uvi", 0),
            ))

        # Daily forecast
        for d in raw.get("daily", []):
            temp = d.get("temp", {})
            feels = d.get("feels_like", {})
            resp.daily.append(pb.DailyForecast(
                dt=d.get("dt", 0),
                temp_day=temp.get("day", 0),
                temp_night=temp.get("night", 0),
                temp_min=temp.get("min", 0),
                temp_max=temp.get("max", 0),
                feels_like_day=feels.get("day", 0),
                feels_like_night=feels.get("night", 0),
                humidity=d.get("humidity", 0),
                pressure=d.get("pressure", 0),
                wind_speed=d.get("wind_speed", 0),
                wind_deg=d.get("wind_deg", 0),
                clouds=d.get("clouds", 0),
                pop=d.get("pop", 0),
                uvi=d.get("uvi", 0),
                weather=self._parse_weather_conditions(d.get("weather", [])),
                sunrise=d.get("sunrise", 0),
                sunset=d.get("sunset", 0),
                summary=d.get("summary", ""),
            ))

        # Alerts
        for a in raw.get("alerts", []):
            resp.alerts.append(pb.WeatherAlert(
                sender_name=a.get("sender_name", ""),
                event=a.get("event", ""),
                start=a.get("start", 0),
                end=a.get("end", 0),
                description=a.get("description", ""),
            ))

        return resp

    def GetHistoricalWeather(self, request: Any, context: Any = None) -> pb.GetHistoricalWeatherResponse:
        raw = self._get("/data/3.0/onecall/timemachine", params={
            "lat": request.lat,
            "lon": request.lon,
            "dt": request.dt,
            "units": "metric",
        })
        resp = pb.GetHistoricalWeatherResponse()
        resp.lat = raw.get("lat", 0)
        resp.lon = raw.get("lon", 0)
        resp.timezone = raw.get("timezone", "")

        data_list = raw.get("data", [])
        if data_list:
            d = data_list[0]
            resp.data.CopyFrom(pb.CurrentWeather(
                temp=d.get("temp", 0),
                feels_like=d.get("feels_like", 0),
                humidity=d.get("humidity", 0),
                pressure=d.get("pressure", 0),
                wind_speed=d.get("wind_speed", 0),
                wind_deg=d.get("wind_deg", 0),
                clouds=d.get("clouds", 0),
                visibility=d.get("visibility", 0),
                weather=self._parse_weather_conditions(d.get("weather", [])),
                sunrise=d.get("sunrise", 0),
                sunset=d.get("sunset", 0),
                dt=d.get("dt", 0),
            ))

        return resp

    def GetWeatherMap(self, request: Any, context: Any = None) -> pb.GetWeatherMapResponse:
        layer = request.layer or "clouds_new"
        url = f"{_TILE_URL}/map/{layer}/{request.z}/{request.x}/{request.y}.png"
        if self._api_key:
            url += f"?appid={self._api_key}"
        return pb.GetWeatherMapResponse(url=url)
