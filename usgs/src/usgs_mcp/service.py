"""USGSService -- wraps USGS public APIs into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from usgs_mcp.gen.usgs.v1 import usgs_pb2 as pb

_EARTHQUAKE_FEED_BASE = "https://earthquake.usgs.gov/earthquakes/feed/v1.0"
_EARTHQUAKE_SEARCH_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
_WATER_SERVICES_URL = "https://waterservices.usgs.gov/nwis/iv/"


def _parse_earthquake(feature: dict) -> pb.Earthquake:
    """Parse a GeoJSON feature into an Earthquake proto message."""
    props = feature.get("properties") or {}
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates") or [0, 0, 0]

    return pb.Earthquake(
        id=feature.get("id", "") or "",
        magnitude=props.get("mag") or 0,
        magnitude_type=props.get("magType", "") or "",
        place=props.get("place", "") or "",
        time=props.get("time") or 0,
        updated=props.get("updated") or 0,
        longitude=coords[0] if len(coords) > 0 else 0,
        latitude=coords[1] if len(coords) > 1 else 0,
        depth=coords[2] if len(coords) > 2 else 0,
        url=props.get("url", "") or "",
        detail_url=props.get("detail", "") or "",
        felt=props.get("felt") or 0,
        cdi=props.get("cdi") or 0,
        mmi=props.get("mmi") or 0,
        alert=props.get("alert", "") or "",
        status=props.get("status", "") or "",
        tsunami=props.get("tsunami") or 0,
        sig=props.get("sig") or 0,
        net=props.get("net", "") or "",
        code=props.get("code", "") or "",
        nst=props.get("nst") or 0,
        dmin=props.get("dmin") or 0,
        rms=props.get("rms") or 0,
        horizontal_error=props.get("horizontalError") or 0,
        depth_error=props.get("depthError") or 0,
        magnitude_error=props.get("magError") or 0,
        magnitude_nst=props.get("magNst") or 0,
        type=props.get("type", "") or "",
        title=props.get("title", "") or "",
    )


def _parse_earthquake_collection(data: dict) -> pb.EarthquakeCollection:
    """Parse a GeoJSON FeatureCollection into an EarthquakeCollection proto."""
    metadata = data.get("metadata") or {}
    features = data.get("features") or []

    earthquakes = []
    for f in features:
        earthquakes.append(_parse_earthquake(f))

    return pb.EarthquakeCollection(
        count=metadata.get("count") or len(earthquakes),
        title=metadata.get("title", "") or "",
        earthquakes=earthquakes,
    )


def _parse_water_level_site(data: dict) -> pb.WaterLevelSite:
    """Parse USGS Water Services JSON into a WaterLevelSite proto."""
    value = data.get("value") or {}
    time_series_list = value.get("timeSeries") or []

    if not time_series_list:
        return pb.WaterLevelSite()

    ts = time_series_list[0]

    # Site info.
    source_info = ts.get("sourceInfo") or {}
    site_number = (source_info.get("siteCode") or [{}])[0].get("value", "") or ""
    site_name = source_info.get("siteName", "") or ""
    geo = source_info.get("geoLocation") or {}
    geo_loc = geo.get("geogLocation") or {}
    latitude = geo_loc.get("latitude") or 0
    longitude = geo_loc.get("longitude") or 0

    # Variable info.
    variable = ts.get("variable") or {}
    variable_desc = variable.get("variableDescription", "") or ""
    unit_obj = variable.get("unit") or {}
    unit = unit_obj.get("unitCode", "") or ""

    # Readings.
    readings = []
    values_list = ts.get("values") or []
    if values_list:
        raw_values = values_list[0].get("value") or []
        for rv in raw_values:
            readings.append(pb.WaterLevelReading(
                datetime=rv.get("dateTime", "") or "",
                value=rv.get("value", "") or "",
            ))

    return pb.WaterLevelSite(
        site_number=site_number,
        site_name=site_name,
        latitude=latitude,
        longitude=longitude,
        readings=readings,
        variable_description=variable_desc,
        unit=unit,
    )


class USGSService:
    """Implements USGSService RPCs via the free USGS public APIs."""

    def __init__(self):
        self._http = httpx.Client(timeout=30, follow_redirects=True)

    def _get(self, url: str, params: dict | None = None) -> Any:
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def GetRecentEarthquakes(self, request: Any, context: Any = None) -> pb.GetRecentEarthquakesResponse:
        raw = self._get(f"{_EARTHQUAKE_FEED_BASE}/summary/all_hour.geojson")
        collection = _parse_earthquake_collection(raw)
        return pb.GetRecentEarthquakesResponse(collection=collection)

    def GetSignificantEarthquakes(self, request: Any, context: Any = None) -> pb.GetSignificantEarthquakesResponse:
        raw = self._get(f"{_EARTHQUAKE_FEED_BASE}/summary/significant_month.geojson")
        collection = _parse_earthquake_collection(raw)
        return pb.GetSignificantEarthquakesResponse(collection=collection)

    def SearchEarthquakes(self, request: Any, context: Any = None) -> pb.SearchEarthquakesResponse:
        params = {"format": "geojson"}
        if request.start_time:
            params["starttime"] = request.start_time
        if request.end_time:
            params["endtime"] = request.end_time
        if request.min_magnitude:
            params["minmagnitude"] = request.min_magnitude
        if request.max_magnitude:
            params["maxmagnitude"] = request.max_magnitude
        if request.min_latitude:
            params["minlatitude"] = request.min_latitude
        if request.max_latitude:
            params["maxlatitude"] = request.max_latitude
        if request.min_longitude:
            params["minlongitude"] = request.min_longitude
        if request.max_longitude:
            params["maxlongitude"] = request.max_longitude
        if request.limit:
            params["limit"] = request.limit
        if request.order_by:
            params["orderby"] = request.order_by

        raw = self._get(_EARTHQUAKE_SEARCH_URL, params=params)
        collection = _parse_earthquake_collection(raw)
        return pb.SearchEarthquakesResponse(collection=collection)

    def GetEarthquakeDetail(self, request: Any, context: Any = None) -> pb.GetEarthquakeDetailResponse:
        raw = self._get(f"{_EARTHQUAKE_FEED_BASE}/detail/{request.event_id}.geojson")
        # Detail endpoint returns a single Feature, not a FeatureCollection.
        earthquake = _parse_earthquake(raw)
        return pb.GetEarthquakeDetailResponse(earthquake=earthquake)

    def GetWaterLevels(self, request: Any, context: Any = None) -> pb.GetWaterLevelsResponse:
        params = {
            "format": "json",
            "sites": request.site_number,
            "parameterCd": "00065",
            "period": "P1D",
        }
        raw = self._get(_WATER_SERVICES_URL, params=params)
        site = _parse_water_level_site(raw)
        return pb.GetWaterLevelsResponse(site=site)
